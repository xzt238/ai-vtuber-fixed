import warnings

warnings.filterwarnings("ignore")
import os

import utils

hps = utils.get_hparams(stage=2)
os.environ["CUDA_VISIBLE_DEVICES"] = hps.train.gpu_numbers.replace("-", ",")
import logging

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.cuda.amp import GradScaler, autocast
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

logging.getLogger("matplotlib").setLevel(logging.INFO)
logging.getLogger("h5py").setLevel(logging.INFO)
logging.getLogger("numba").setLevel(logging.INFO)
from random import randint

from module import commons
from module.data_utils import (
    DistributedBucketSampler,
)
from module.data_utils import (
    TextAudioSpeakerCollateV3 as TextAudioSpeakerCollate,
)
from module.data_utils import (
    TextAudioSpeakerLoaderV3 as TextAudioSpeakerLoader,
)
from module.models import (
    SynthesizerTrnV3 as SynthesizerTrn,
)
from process_ckpt import savee

torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = False
###反正A100fp32更快，那试试tf32吧
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.set_float32_matmul_precision("medium")  # 最低精度但最快（也就快一丁点），对于结果造成不了影响
# from config import pretrained_s2G,pretrained_s2D
global_step = 0

device = "cpu"  # cuda以外的设备，等mps优化后加入


def main():
    if torch.cuda.is_available():
        n_gpus = torch.cuda.device_count()
    else:
        n_gpus = 1
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = str(randint(20000, 55555))

    mp.spawn(
        run,
        nprocs=n_gpus,
        args=(
            n_gpus,
            hps,
        ),
    )


def run(rank, n_gpus, hps):
    global global_step
    if rank == 0:
        logger = utils.get_logger(hps.data.exp_dir)
        logger.info(hps)
        # utils.check_git_hash(hps.s2_ckpt_dir)
        writer = SummaryWriter(log_dir=hps.s2_ckpt_dir)
        writer_eval = SummaryWriter(log_dir=os.path.join(hps.s2_ckpt_dir, "eval"))

    # Windows (os.name == "nt") 上跳过 torch.distributed，单进程训练避免 libuv 问题
    # （PyTorch Windows build 未包含 libuv 支持，init_method/store 相关 API 均会报错）
    _single_process = os.name == "nt" or n_gpus == 1
    if not _single_process:
        if torch.cuda.is_available():
            dist.init_process_group(backend="nccl", init_method="env://", world_size=n_gpus, rank=rank)
        else:
            dist.init_process_group(backend="gloo", init_method="env://", world_size=n_gpus, rank=rank)
    # else: 完全跳过 distributed，单进程直接跑
    torch.manual_seed(hps.train.seed)
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)

    train_dataset = TextAudioSpeakerLoader(hps.data)  ########

    if _single_process:
        # 单进程：使用普通 DataLoader + RandomSampler（绕过 DistributedBucketSampler）
        train_loader = DataLoader(
            train_dataset,
            batch_size=hps.train.batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=False,
            collate_fn=TextAudioSpeakerCollate(),
            drop_last=True,
        )
    else:
        train_sampler = DistributedBucketSampler(
            train_dataset,
            hps.train.batch_size,
            [
                32,
                300,
                400,
                500,
                600,
                700,
                800,
                900,
                1000,
            ],
            num_replicas=n_gpus,
            rank=rank,
            shuffle=True,
        )
        _nw = 0 if os.name == "nt" else 5
        train_loader = DataLoader(
            train_dataset,
            num_workers=_nw,
            shuffle=False,
            pin_memory=False,
            collate_fn=TextAudioSpeakerCollate(),
            batch_sampler=train_sampler,
            persistent_workers=False if _nw == 0 else True,
            prefetch_factor=None if _nw == 0 else 3,
        )
    # if rank == 0:
    #     eval_dataset = TextAudioSpeakerLoader(hps.data.validation_files, hps.data, val=True)
    #     eval_loader = DataLoader(eval_dataset, num_workers=0, shuffle=False,
    #                              batch_size=1, pin_memory=True,
    #                              drop_last=False, collate_fn=collate_fn)

    # 单进程时直接创建模型，不走 DDP；多进程时用 DDP 包装
    if _single_process:
        net_g = (
            SynthesizerTrn(
                hps.data.filter_length // 2 + 1,
                hps.train.segment_size // hps.data.hop_length,
                n_speakers=hps.data.n_speakers,
                **hps.model,
            )
            .cuda() if torch.cuda.is_available()
            else SynthesizerTrn(
                hps.data.filter_length // 2 + 1,
                hps.train.segment_size // hps.data.hop_length,
                n_speakers=hps.data.n_speakers,
                **hps.model,
            ).to(device)
        )
    else:
        net_g = (
            SynthesizerTrn(
                hps.data.filter_length // 2 + 1,
                hps.train.segment_size // hps.data.hop_length,
                n_speakers=hps.data.n_speakers,
                **hps.model,
            ).cuda(rank)
            if torch.cuda.is_available()
            else SynthesizerTrn(
                hps.data.filter_length // 2 + 1,
                hps.train.segment_size // hps.data.hop_length,
                n_speakers=hps.data.n_speakers,
                **hps.model,
            ).to(device)
        )

    # net_d = MultiPeriodDiscriminator(hps.model.use_spectral_norm).cuda(rank) if torch.cuda.is_available() else MultiPeriodDiscriminator(hps.model.use_spectral_norm).to(device)
    # for name, param in net_g.named_parameters():
    #     if not param.requires_grad:
    #         print(name, "not requires_grad")

    optim_g = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, net_g.parameters()),  ###默认所有层lr一致
        hps.train.learning_rate,
        betas=hps.train.betas,
        eps=hps.train.eps,
    )
    # optim_d = torch.optim.AdamW(
    #     net_d.parameters(),
    #     hps.train.learning_rate,
    #     betas=hps.train.betas,
    #     eps=hps.train.eps,
    # )
    if not _single_process and torch.cuda.is_available():
        net_g = DDP(net_g, device_ids=[rank], find_unused_parameters=True)
        # net_d = DDP(net_d, device_ids=[rank], find_unused_parameters=True)
    elif not _single_process:
        net_g = net_g.to(device)
        # net_d = net_d.to(device)

    try:  # 如果能加载自动resume
        # _, _, _, epoch_str = utils.load_checkpoint(
        #     utils.latest_checkpoint_path("%s/logs_s2_%s" % (hps.data.exp_dir,hps.model.version), "D_*.pth"),
        #     net_d,
        #     optim_d,
        # )  # D多半加载没事
        # if rank == 0:
        #     logger.info("loaded D")
        # _, _, _, epoch_str = utils.load_checkpoint(utils.latest_checkpoint_path(hps.model_dir, "G_*.pth"), net_g, optim_g,load_opt=0)
        _, _, _, epoch_str = utils.load_checkpoint(
            utils.latest_checkpoint_path("%s/logs_s2_%s" % (hps.data.exp_dir, hps.model.version), "G_*.pth"),
            net_g,
            optim_g,
        )
        epoch_str += 1
        global_step = (epoch_str - 1) * len(train_loader)
        # epoch_str = 1
        # global_step = 0
    except:  # 如果首次不能加载，加载pretrain
        # traceback.print_exc()
        epoch_str = 1
        global_step = 0
        if (
            hps.train.pretrained_s2G != ""
            and hps.train.pretrained_s2G != None
            and os.path.exists(hps.train.pretrained_s2G)
        ):
            if rank == 0:
                logger.info("loaded pretrained %s" % hps.train.pretrained_s2G)
            print(
                "loaded pretrained %s" % hps.train.pretrained_s2G,
                net_g.module.load_state_dict(
                    torch.load(hps.train.pretrained_s2G, map_location="cpu", weights_only=False)["weight"],
                    strict=False,
                )
                if torch.cuda.is_available()
                else net_g.load_state_dict(
                    torch.load(hps.train.pretrained_s2G, map_location="cpu", weights_only=False)["weight"],
                    strict=False,
                ),
            )  ##测试不加载优化器
        # if hps.train.pretrained_s2D != ""and hps.train.pretrained_s2D != None and os.path.exists(hps.train.pretrained_s2D):
        #     if rank == 0:
        #         logger.info("loaded pretrained %s" % hps.train.pretrained_s2D)
        #     print(
        #         net_d.module.load_state_dict(
        #             torch.load(hps.train.pretrained_s2D, map_location="cpu")["weight"]
        #         ) if torch.cuda.is_available() else net_d.load_state_dict(
        #             torch.load(hps.train.pretrained_s2D, map_location="cpu")["weight"]
        #         )
        #     )

    # scheduler_g = torch.optim.lr_scheduler.ExponentialLR(optim_g, gamma=hps.train.lr_decay, last_epoch=epoch_str - 2)
    # scheduler_d = torch.optim.lr_scheduler.ExponentialLR(optim_d, gamma=hps.train.lr_decay, last_epoch=epoch_str - 2)

    scheduler_g = torch.optim.lr_scheduler.ExponentialLR(optim_g, gamma=hps.train.lr_decay, last_epoch=-1)
    # scheduler_d = torch.optim.lr_scheduler.ExponentialLR(
    #     optim_d, gamma=hps.train.lr_decay, last_epoch=-1
    # )
    for _ in range(epoch_str):
        scheduler_g.step()
        # scheduler_d.step()

    scaler = GradScaler(enabled=hps.train.fp16_run)

    net_d = optim_d = scheduler_d = None
    print("start training from epoch %s" % epoch_str)
    for epoch in range(epoch_str, hps.train.epochs + 1):
        if rank == 0:
            train_and_evaluate(
                rank,
                epoch,
                hps,
                [net_g, net_d],
                [optim_g, optim_d],
                [scheduler_g, scheduler_d],
                scaler,
                # [train_loader, eval_loader], logger, [writer, writer_eval])
                [train_loader, None],
                logger,
                [writer, writer_eval],
            )
        else:
            train_and_evaluate(
                rank,
                epoch,
                hps,
                [net_g, net_d],
                [optim_g, optim_d],
                [scheduler_g, scheduler_d],
                scaler,
                [train_loader, None],
                None,
                None,
            )
        scheduler_g.step()
        # scheduler_d.step()
    print("training done")


def train_and_evaluate(
    rank,
    epoch,
    hps,
    nets,
    optims,
    schedulers,
    scaler,
    loaders,
    logger,
    writers,
):
    net_g, net_d = nets
    optim_g, optim_d = optims
    # scheduler_g, scheduler_d = schedulers
    train_loader, eval_loader = loaders
    if writers is not None:
        writer, writer_eval = writers

    train_loader.batch_sampler.set_epoch(epoch)
    global global_step

    net_g.train()
    # net_d.train()
    print(f"[train_and_evaluate] epoch={epoch}, total_batches={len(train_loader)}, batch_size={train_loader.batch_size}", flush=True)
    print("[train_and_evaluate] entering training loop...", flush=True)
    # for batch_idx, (
    #     ssl,
    #     ssl_lengths,
    #     spec,
    #     spec_lengths,
    #     y,
    #     y_lengths,
    #     text,
    #     text_lengths,
    # ) in enumerate(tqdm(train_loader)):
    for batch_idx, (ssl, spec, mel, ssl_lengths, spec_lengths, text, text_lengths, mel_lengths) in enumerate(
        tqdm(train_loader)
    ):
        print(f"[DEBUG] batch_idx={batch_idx}: data loaded, shapes: ssl={ssl.shape}, mel={mel.shape}", flush=True)
        if torch.cuda.is_available():
            spec, spec_lengths = spec.cuda(rank), spec_lengths.cuda(rank)
            mel, mel_lengths = mel.cuda(rank), mel_lengths.cuda(rank)
            ssl = ssl.cuda(rank)
            ssl.requires_grad = False
            text, text_lengths = text.cuda(rank), text_lengths.cuda(rank)
        else:
            spec, spec_lengths = spec.to(device), spec_lengths.to(device)
            mel, mel_lengths = mel.to(device), mel_lengths.to(device)
            ssl = ssl.to(device)
            ssl.requires_grad = False
            text, text_lengths = text.to(device), text_lengths.to(device)

        print(f"[DEBUG] batch_idx={batch_idx}: data to GPU done", flush=True)
        with autocast(enabled=hps.train.fp16_run):
            cfm_loss = net_g(
                ssl,
                spec,
                mel,
                ssl_lengths,
                spec_lengths,
                text,
                text_lengths,
                mel_lengths,
                use_grad_ckpt=hps.train.grad_ckpt,
            )
            loss_gen_all = cfm_loss
        print(f"[DEBUG] batch_idx={batch_idx}: forward done, loss={loss_gen_all.item():.6f}", flush=True)
        optim_g.zero_grad()
        scaler.scale(loss_gen_all).backward()
        print(f"[DEBUG] batch_idx={batch_idx}: backward done", flush=True)
        scaler.unscale_(optim_g)
        grad_norm_g = commons.clip_grad_value_(net_g.parameters(), None)
        scaler.step(optim_g)
        scaler.update()
        print(f"[DEBUG] batch_idx={batch_idx}: optimizer step done", flush=True)

        if rank == 0:
            if global_step % hps.train.log_interval == 0:
                lr = optim_g.param_groups[0]["lr"]
                # losses = [commit_loss,cfm_loss,mel_loss,loss_disc, loss_gen, loss_fm, loss_mel, loss_kl]
                losses = [cfm_loss]
                logger.info(
                    "Train Epoch: {} [{:.0f}%]".format(
                        epoch,
                        100.0 * batch_idx / len(train_loader),
                    )
                )
                logger.info([x.item() for x in losses] + [global_step, lr])

                scalar_dict = {"loss/g/total": loss_gen_all, "learning_rate": lr, "grad_norm_g": grad_norm_g}
                # image_dict = {
                #     "slice/mel_org": utils.plot_spectrogram_to_numpy(y_mel[0].data.cpu().numpy()),
                #     "slice/mel_gen": utils.plot_spectrogram_to_numpy(y_hat_mel[0].data.cpu().numpy()),
                #     "all/mel": utils.plot_spectrogram_to_numpy(mel[0].data.cpu().numpy()),
                #     "all/stats_ssl": utils.plot_spectrogram_to_numpy(stats_ssl[0].data.cpu().numpy()),
                # }
                utils.summarize(
                    writer=writer,
                    global_step=global_step,
                    # images=image_dict,
                    scalars=scalar_dict,
                )

            # if global_step % hps.train.eval_interval == 0:
            #     # evaluate(hps, net_g, eval_loader, writer_eval)
            #     utils.save_checkpoint(net_g, optim_g, hps.train.learning_rate, epoch,os.path.join(hps.s2_ckpt_dir, "G_{}.pth".format(global_step)),scaler)
            #     # utils.save_checkpoint(net_d, optim_d, hps.train.learning_rate, epoch,os.path.join(hps.s2_ckpt_dir, "D_{}.pth".format(global_step)),scaler)
            #     # keep_ckpts = getattr(hps.train, 'keep_ckpts', 3)
            #     # if keep_ckpts > 0:
            #     #     utils.clean_checkpoints(path_to_models=hps.s2_ckpt_dir, n_ckpts_to_keep=keep_ckpts, sort_by_time=True)

        global_step += 1
    if epoch % hps.train.save_every_epoch == 0 and rank == 0:
        if hps.train.if_save_latest == 0:
            utils.save_checkpoint(
                net_g,
                optim_g,
                hps.train.learning_rate,
                epoch,
                os.path.join(
                    "%s/logs_s2_%s" % (hps.data.exp_dir, hps.model.version),
                    "G_{}.pth".format(global_step),
                ),
            )
            # utils.save_checkpoint(
            #     net_d,
            #     optim_d,
            #     hps.train.learning_rate,
            #     epoch,
            #     os.path.join(
            #         "%s/logs_s2_%s" % (hps.data.exp_dir,hps.model.version), "D_{}.pth".format(global_step)
            #     ),
            # )
        else:
            utils.save_checkpoint(
                net_g,
                optim_g,
                hps.train.learning_rate,
                epoch,
                os.path.join(
                    "%s/logs_s2_%s" % (hps.data.exp_dir, hps.model.version),
                    "G_{}.pth".format(233333333333),
                ),
            )
            # utils.save_checkpoint(
            #     net_d,
            #     optim_d,
            #     hps.train.learning_rate,
            #     epoch,
            #     os.path.join(
            #         "%s/logs_s2_%s" % (hps.data.exp_dir,hps.model.version), "D_{}.pth".format(233333333333)
            #     ),
            # )
        if rank == 0 and hps.train.if_save_every_weights == True:
            if hasattr(net_g, "module"):
                ckpt = net_g.module.state_dict()
            else:
                ckpt = net_g.state_dict()
            logger.info(
                "saving ckpt %s_e%s:%s"
                % (
                    hps.name,
                    epoch,
                    savee(
                        ckpt,
                        hps.name + "_e%s_s%s" % (epoch, global_step),
                        epoch,
                        global_step,
                        hps,
                    ),
                )
            )

    if rank == 0:
        logger.info("====> Epoch: {}".format(epoch))


if __name__ == "__main__":
    main()

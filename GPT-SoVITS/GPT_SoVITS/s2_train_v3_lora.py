import warnings

warnings.filterwarnings("ignore")
import os
import socket

import utils


def find_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


hps = utils.get_hparams(stage=2)
os.environ["CUDA_VISIBLE_DEVICES"] = hps.train.gpu_numbers.replace("-", ",")
import logging

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.cuda.amp import GradScaler, autocast
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, RandomSampler
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

logging.getLogger("matplotlib").setLevel(logging.INFO)
logging.getLogger("h5py").setLevel(logging.INFO)
logging.getLogger("numba").setLevel(logging.INFO)
from collections import OrderedDict as od

import time

from module import commons
from module.data_utils import (
    DistributedBucketSampler,
    TextAudioSpeakerCollateV3,
    TextAudioSpeakerLoaderV3,
    TextAudioSpeakerCollateV4,
    TextAudioSpeakerLoaderV4,
)
from module.models import (
    SynthesizerTrnV3 as SynthesizerTrn,
)
from peft import LoraConfig, get_peft_model
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
    os.environ["MASTER_PORT"] = str(find_free_port())

    # Windows: bypass mp.spawn entirely to avoid torch.multiprocessing.spawn
    # which uses Windows DLLs that crash with gloo/libuv. Direct call on main process.
    if os.name == "nt":
        run(0, n_gpus, hps)
    else:
        mp.spawn(
            run,
            nprocs=n_gpus,
            args=(
                n_gpus,
                hps,
            ),
        )


def run(rank, n_gpus, hps):
    global global_step, no_grad_names, save_root, lora_rank
    if rank == 0:
        logger = utils.get_logger(hps.data.exp_dir)
        logger.info(hps)
        # utils.check_git_hash(hps.s2_ckpt_dir)
        writer = SummaryWriter(log_dir=hps.s2_ckpt_dir)
        writer_eval = SummaryWriter(log_dir=os.path.join(hps.s2_ckpt_dir, "eval"))

    dist.init_process_group(
        backend="gloo" if os.name == "nt" or not torch.cuda.is_available() else "nccl",
        init_method="env://?use_libuv=False",
        world_size=n_gpus,
        rank=rank,
    )
    torch.manual_seed(hps.train.seed)
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)

    TextAudioSpeakerLoader = TextAudioSpeakerLoaderV3 if hps.model.version == "v3" else TextAudioSpeakerLoaderV4
    TextAudioSpeakerCollate = TextAudioSpeakerCollateV3 if hps.model.version == "v3" else TextAudioSpeakerCollateV4
    train_dataset = TextAudioSpeakerLoader(hps.data)  ########
    # Windows multiprocessing: DistributedBucketSampler causes deadlocks even with num_workers=0
    # and even with num_replicas=1, it uses torch.distributed internally which can hang on Windows
    # Replace with simple RandomSampler on Windows (single-process mode, no distributed at all)
    global _has_set_epoch_flag
    _win_single = os.name == "nt"
    if _win_single:
        train_sampler = RandomSampler(train_dataset)
        _has_set_epoch_flag = False
    else:
        train_sampler = DistributedBucketSampler(
            train_dataset,
            hps.train.batch_size,
            [32, 300, 400, 500, 600, 700, 800, 900, 1000],
            num_replicas=n_gpus,
            rank=rank,
            shuffle=True,
        )
        _has_set_epoch_flag = True
    collate_fn = TextAudioSpeakerCollate()
    # Windows multiprocessing: num_workers>0 causes deadlocks due to Windows spawn semantics
    # Set num_workers=0, pin_memory=False, persistent_workers=False for Windows compatibility
    _dl_workers = 0 if os.name == "nt" else 5
    _pin_memory = False if os.name == "nt" else True
    _persistent = False if os.name == "nt" else True
    _prefetch = None if os.name == "nt" else 3
    # CRITICAL: PyTorch 2.5.1 with RandomSampler as batch_sampler fails because
    # RandomSampler yields individual indices but _auto_collation=True collates them wrongly.
    # Windows: use sampler + batch_size (standard pattern, auto-creates BatchSampler)
    # Linux/multi-GPU: use batch_sampler=DistributedBucketSampler (yields proper batches)
    if _win_single:
        train_loader = DataLoader(
            train_dataset,
            sampler=train_sampler,  # RandomSampler
            batch_size=hps.train.batch_size,
            num_workers=_dl_workers,
            pin_memory=_pin_memory,
            collate_fn=collate_fn,
            drop_last=True,
            persistent_workers=_persistent,
            prefetch_factor=_prefetch,
        )
    else:
        train_loader = DataLoader(
            train_dataset,
            batch_size=1,  # ignored when batch_sampler is set, but kept for consistency
            num_workers=_dl_workers,
            pin_memory=_pin_memory,
            collate_fn=collate_fn,
            batch_sampler=train_sampler,  # DistributedBucketSampler
            persistent_workers=_persistent,
            prefetch_factor=_prefetch,
        )
    save_root = "%s/logs_s2_%s_lora_%s" % (hps.data.exp_dir, hps.model.version, hps.train.lora_rank)
    os.makedirs(save_root, exist_ok=True)
    lora_rank = int(hps.train.lora_rank)
    lora_config = LoraConfig(
        target_modules=["to_k", "to_q", "to_v", "to_out.0"],
        r=lora_rank,
        lora_alpha=lora_rank,
        init_lora_weights=True,
    )

    def get_model(hps):
        return SynthesizerTrn(
            hps.data.filter_length // 2 + 1,
            hps.train.segment_size // hps.data.hop_length,
            n_speakers=hps.data.n_speakers,
            **hps.model,
        )

    def get_optim(net_g):
        return torch.optim.AdamW(
            filter(lambda p: p.requires_grad, net_g.parameters()),  ###默认所有层lr一致
            hps.train.learning_rate,
            betas=hps.train.betas,
            eps=hps.train.eps,
        )

    def model2cuda(net_g, rank):
        if torch.cuda.is_available():
            net_g = DDP(net_g.cuda(rank), device_ids=[rank], find_unused_parameters=True)
        else:
            net_g = net_g.to(device)
        return net_g

    try:  # 如果能加载自动resume
        net_g = get_model(hps)
        net_g.cfm = get_peft_model(net_g.cfm, lora_config)
        net_g = model2cuda(net_g, rank)
        optim_g = get_optim(net_g)
        # _, _, _, epoch_str = utils.load_checkpoint(utils.latest_checkpoint_path(hps.model_dir, "G_*.pth"), net_g, optim_g,load_opt=0)
        _, _, _, epoch_str = utils.load_checkpoint(
            utils.latest_checkpoint_path(save_root, "G_*.pth"),
            net_g,
            optim_g,
        )
        epoch_str += 1
        global_step = (epoch_str - 1) * len(train_loader)
    except:  # 如果首次不能加载，加载pretrain
        # traceback.print_exc()
        epoch_str = 1
        global_step = 0
        net_g = get_model(hps)
        if (
            hps.train.pretrained_s2G != ""
            and hps.train.pretrained_s2G != None
            and os.path.exists(hps.train.pretrained_s2G)
        ):
            if rank == 0:
                logger.info("loaded pretrained %s" % hps.train.pretrained_s2G)
            print(
                "loaded pretrained %s" % hps.train.pretrained_s2G,
                net_g.load_state_dict(
                    torch.load(hps.train.pretrained_s2G, map_location="cpu", weights_only=False)["weight"],
                    strict=False,
                ),
            )
        net_g.cfm = get_peft_model(net_g.cfm, lora_config)
        net_g = model2cuda(net_g, rank)
        optim_g = get_optim(net_g)

    no_grad_names = set()
    for name, param in net_g.named_parameters():
        if not param.requires_grad:
            no_grad_names.add(name.replace("module.", ""))
            # print(name, "not requires_grad")
    # print(no_grad_names)
    # os._exit(233333)

    scheduler_g = torch.optim.lr_scheduler.ExponentialLR(optim_g, gamma=hps.train.lr_decay, last_epoch=-1)
    for _ in range(epoch_str):
        scheduler_g.step()

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
    print("training done")


def train_and_evaluate(rank, epoch, hps, nets, optims, schedulers, scaler, loaders, logger, writers):
    net_g, net_d = nets
    optim_g, optim_d = optims
    # scheduler_g, scheduler_d = schedulers
    train_loader, eval_loader = loaders
    if writers is not None:
        writer, writer_eval = writers

    # RandomSampler on Windows has no set_epoch, only DistributedBucketSampler does
    global _has_set_epoch_flag
    if _has_set_epoch_flag:
        train_loader.batch_sampler.set_epoch(epoch)
    global global_step

    net_g.train()
    _dl_time = None
    for batch_idx, (ssl, spec, mel, ssl_lengths, spec_lengths, text, text_lengths, mel_lengths) in enumerate(
        tqdm(train_loader)
    ):
        if _dl_time is None:
            _dl_time = time.time()
        if batch_idx == 0:
            print(f"[TIMING] DataLoader first batch ready, shapes: ssl={ssl.shape}, mel={mel.shape}, mel_lengths={mel_lengths.tolist()}", flush=True)
        if torch.cuda.is_available():
            spec, spec_lengths = (
                spec.cuda(
                    rank,
                    non_blocking=True,
                ),
                spec_lengths.cuda(
                    rank,
                    non_blocking=True,
                ),
            )
            mel, mel_lengths = mel.cuda(rank, non_blocking=True), mel_lengths.cuda(rank, non_blocking=True)
            ssl = ssl.cuda(rank, non_blocking=True)
            ssl.requires_grad = False
            text, text_lengths = (
                text.cuda(
                    rank,
                    non_blocking=True,
                ),
                text_lengths.cuda(
                    rank,
                    non_blocking=True,
                ),
            )
        else:
            spec, spec_lengths = spec.to(device), spec_lengths.to(device)
            mel, mel_lengths = mel.to(device), mel_lengths.to(device)
            ssl = ssl.to(device)
            ssl.requires_grad = False
            text, text_lengths = text.to(device), text_lengths.to(device)

        if global_step == 1:
            torch.cuda.synchronize()
            _t0 = time.time()
        with autocast(enabled=hps.train.fp16_run):
            _t_net_start = time.time()
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
            _t_net_end = time.time()
            loss_gen_all = cfm_loss
        if global_step == 1:
            torch.cuda.synchronize()
            _t1 = time.time()
            print(f"[TIMING] batch0 net_g() call: {_t_net_end-_t_net_start:.1f}s", flush=True)
            print(f"[TIMING] batch0 forward total: {_t1-_t0:.1f}s, cfm_loss={cfm_loss.item():.6f}", flush=True)
        optim_g.zero_grad()
        _tb_start = time.time()
        scaler.scale(loss_gen_all).backward()
        if global_step == 1:
            torch.cuda.synchronize()
            _t2 = time.time()
            print(f"[TIMING] batch0 backward: {_t2-_tb_start:.1f}s", flush=True)
        scaler.unscale_(optim_g)
        grad_norm_g = commons.clip_grad_value_(net_g.parameters(), None)
        scaler.step(optim_g)
        scaler.update()
        if global_step == 1:
            torch.cuda.synchronize()
            _t3 = time.time()
            print(f"[TIMING] batch0 optim+step: {_t3-_t2:.1f}s", flush=True)
            print(f"[TIMING] batch0 TOTAL (dataloader excluded): {_t3-_t0:.1f}s", flush=True)

        if rank == 0:
            if global_step % hps.train.log_interval == 0:
                lr = optim_g.param_groups[0]["lr"]
                losses = [cfm_loss]
                logger.info("Train Epoch: {} [{:.0f}%]".format(epoch, 100.0 * batch_idx / len(train_loader)))
                logger.info([x.item() for x in losses] + [global_step, lr])

                scalar_dict = {"loss/g/total": loss_gen_all, "learning_rate": lr, "grad_norm_g": grad_norm_g}
                utils.summarize(
                    writer=writer,
                    global_step=global_step,
                    scalars=scalar_dict,
                )

        global_step += 1
    if epoch % hps.train.save_every_epoch == 0 and rank == 0:
        if hps.train.if_save_latest == 0:
            utils.save_checkpoint(
                net_g,
                optim_g,
                hps.train.learning_rate,
                epoch,
                os.path.join(save_root, "G_{}.pth".format(global_step)),
            )
        else:
            utils.save_checkpoint(
                net_g,
                optim_g,
                hps.train.learning_rate,
                epoch,
                os.path.join(save_root, "G_{}.pth".format(233333333333)),
            )
        if rank == 0 and hps.train.if_save_every_weights == True:
            if hasattr(net_g, "module"):
                ckpt = net_g.module.state_dict()
            else:
                ckpt = net_g.state_dict()
            sim_ckpt = od()
            for key in ckpt:
                # if "cfm"not in key:
                #     print(key)
                if key not in no_grad_names:
                    sim_ckpt[key] = ckpt[key].half().cpu()
            logger.info(
                "saving ckpt %s_e%s:%s"
                % (
                    hps.name,
                    epoch,
                    savee(
                        sim_ckpt,
                        hps.name + "_e%s_s%s_l%s" % (epoch, global_step, lora_rank),
                        epoch,
                        global_step,
                        hps,
                        model_version=hps.model.version,
                        lora_rank=lora_rank,
                    ),
                )
            )

    if rank == 0:
        logger.info("====> Epoch: {}".format(epoch))


if __name__ == "__main__":
    main()

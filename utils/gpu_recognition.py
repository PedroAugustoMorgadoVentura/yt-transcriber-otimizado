import torch


def Gpu_Recognition():
    major, minor = torch.cuda.get_device_capability(0)
    capability = float(f"{major}.{minor}")
    return capability
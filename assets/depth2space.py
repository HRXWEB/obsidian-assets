import torch
import torch.nn as nn
from torch.autograd import Function
import torch.onnx
import onnx
import onnxruntime as ort

class DepthToSpace_DCR(Function):
    @staticmethod
    def forward(ctx, input, block_size, mode):
        b, c, h, w = input.size()
        tmp = input.view(b, block_size, block_size, c // (block_size ** 2), h, w)
        tmp = tmp.permute(0, 3, 4, 1, 5, 2).contiguous()
        y = tmp.view(b, c // (block_size ** 2), h * block_size, w * block_size)
        return y

    @staticmethod
    def symbolic(g, input, block_size, mode):
        return g.op("DepthToSpace", input, blocksize_i=block_size, mode_s=mode)
    
class DepthToSpace_CRD(Function):
    @staticmethod
    def forward(ctx, input, block_size, mode):
        b, c, h, w = input.size()
        tmp = input.view(b, c // (block_size ** 2), block_size, block_size, h, w)
        tmp = tmp.permute(0, 1, 4, 2, 5, 3).contiguous()
        y = tmp.view(b, c // (block_size ** 2), h * block_size, w * block_size)
        return y

    @staticmethod
    def symbolic(g, input, block_size, mode):
        return g.op("DepthToSpace", input, blocksize_i=block_size, mode_s=mode)
    
class DepthToSpace_DCR_Module(nn.Module):
    def __init__(self, block_size, mode='DCR'):
        super(DepthToSpace_DCR_Module, self).__init__()
        self.block_size = block_size
        self.mode = mode

    def forward(self, x):
        return DepthToSpace_DCR.apply(x, self.block_size, self.mode)
    
class DepthToSpace_CRD_Module(nn.Module):
    def __init__(self, block_size, mode='CRD'):
        super(DepthToSpace_CRD_Module, self).__init__()
        self.block_size = block_size
        self.mode = mode

    def forward(self, x):
        return DepthToSpace_CRD.apply(x, self.block_size, self.mode)
    
def create_model(block_size, mode):
    if mode == 'DCR':
        return DepthToSpace_DCR_Module(block_size)
    elif mode == 'CRD':
        return DepthToSpace_CRD_Module(block_size)
    else:
        raise ValueError("Unknown mode: {}".format(mode))
    
def export_onnx(model, x, onnx_path):
    torch.onnx.export(model, x, onnx_path, opset_version=11,
                      input_names=['input'], output_names=['output'])
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    print("Model is checked!")

def test_depth_to_space():
    x = torch.tensor([[[[0, 2], [8, 10]], [[0, 2], [8, 10]], [[1, 3], [9, 11]], [[1, 3], [9, 11]], [[4, 6], [12, 14]], [[4, 6], [12, 14]], [[5, 7], [13, 15]], [[5, 7], [13, 15]]]], dtype=torch.float32)
    print(f"Input: \n{x}")
    block_size = 2
    modes = ['DCR', 'CRD']
    for mode in modes:
        model = create_model(block_size, mode)
        model_name = "depth_to_space_" + mode + ".onnx"
        export_onnx(model, x, model_name)
        ort_session = ort.InferenceSession(model_name)
        outputs = ort_session.run(None, {'input': x.numpy()})
        print(f"Mode: {mode}, output: \n{outputs[0]}")

    pixel_shuffle = nn.PixelShuffle(2)
    y = pixel_shuffle(x).detach().numpy()
    print(f"PixelShuffle output: \n{y}")

    # pixelshuffle的输出和自定义的DepthToSpace_CRD的输出应该是一样的
    assert torch.allclose(torch.tensor(y), torch.tensor(outputs[0]), atol=1e-6), "Outputs are not equal!"



if __name__ == "__main__":
    test_depth_to_space()
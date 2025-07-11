import cv2
import numpy as np
import torch
from od3d.cv.visual.blend import rgb_to_range01

# Initialize variables to store the coordinates
clicked_position = None


def pick_pixel(img):  #
    # img: 3xHxW
    img_cv = tensor_to_cv_img(img)

    import cv2

    def get_pixel_location(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:  # Left mouse button click
            global clicked_position
            clicked_position = torch.LongTensor([x, y])  # Store the coordinates
            pixel_value = img_cv[y, x]
            print(f"Clicked pixel at {clicked_position}: Value = {pixel_value}")

    # Load the image

    # Create a window and bind the mouse callback function
    cv2.namedWindow("Image")
    cv2.setMouseCallback("Image", get_pixel_location)

    # Display the image and wait for a key press to exit
    while True:
        cv2.imshow("Image", img_cv)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    global clicked_position
    # Check if a pixel was clicked and print the coordinates
    if clicked_position is not None:
        clicked_position = clicked_position.to(device=img.device)
        print("Last clicked position:", clicked_position)

    cv2.destroyAllWindows()
    return clicked_position


def random_colors_as_img(K: int, res=100, device="cpu"):
    colors = get_colors(K * 3, device=device)
    colors = colors[torch.randperm(K * 3).to(device=device)]
    img = torch.zeros(size=(3, res, res * K)).to(device=device)
    for k in range(K):
        img[:, :, res * k : res * (k + 1)] = colors[k][:, None, None].repeat(
            1,
            res,
            res,
        )
    return img


def tensor_to_cv_img(x_in):
    # x_in : CxHxW float32
    # x_out : HxWxC uint8
    if x_in.dtype == torch.uint8:
        x_in = x_in * 1.0
    else:
        x_in = rgb_to_range01(x_in) * 255.0
        # x_in = x_in * 255.0
    x_in = torch.clamp(x_in, min=0.0, max=255.0)
    x_out = (x_in.permute(1, 2, 0).cpu().detach().numpy()).astype(np.uint8)
    x_out = x_out[:, :, ::-1]
    return x_out


from typing import List


def add_boolean_table(img: torch.Tensor, table: torch.Tensor, text: List = None):
    """
    Args:
        img (torch.Tensor): 3xHxW
        table (torch.Tensor): RxC
        W: int
    Return:
        img (torch.Tensor): 3xHxW
    """
    dtype = img.dtype
    device = img.device

    W = img.shape[-1]
    R, C = table.shape
    K = R * C
    column_offset = W // 4
    margin = 5
    entry_width = (W) // C
    font_scale = entry_width / 60.0
    margin_top = int(40 * font_scale)
    H = R * entry_width
    letters_count_max = 0
    if text is not None:
        for t, _text in enumerate(text):
            if len(_text) > letters_count_max:
                letters_count_max = len(_text)
    W_text = int(font_scale * letters_count_max * 20.0)

    img_text = torch.ones(size=(3, H, W_text)).to(dtype=dtype, device=device)
    img_table = torch.ones(size=(3, H, W)).to(dtype=dtype, device=device)

    if text is not None:
        for t, _text in enumerate(text):
            img_text = draw_text_in_rgb(
                img=img_text,
                text=_text,
                leftTopCornerOfText=(margin, margin + margin_top + entry_width * t),
                fontColor=(0, 0, 0),
                fontScale=font_scale,
            )

    pxls = torch.stack(
        torch.meshgrid(torch.arange(R), torch.arange(C), indexing="ij"),
        dim=-1,
    )
    pxls = pxls.flip(dims=[-1])  # x, y
    pxls = ((pxls + 0.5) * entry_width).to(dtype=int, device=device)
    # pxls[:, :, 0] += column_offset
    pxls = pxls.reshape(-1, 2)
    K = pxls.shape[0]
    blue = torch.Tensor([0, 0, 1.0]).to(dtype=dtype, device=device)
    green = torch.Tensor([0, 1.0, 0]).to(dtype=dtype, device=device)
    colors = (
        table[..., None].to(dtype=dtype, device=device) * green[None, None]
        + (~table[..., None]).to(dtype=dtype, device=device) * blue[None, None]
    )
    colors = colors.reshape(-1, 3)
    img_table = (
        draw_pixels(
            img_table,
            pxls=pxls,
            colors=colors,
            radius_in=0,
            radius_out=entry_width // 5,
        )
        / 255.0
    )

    img_table = torch.cat([img_text, img_table], dim=-1)

    img = torch.cat(
        [
            torch.ones(img.shape[0], img.shape[1], W_text).to(
                dtype=dtype,
                device=device,
            ),
            img,
        ],
        dim=-1,
    )
    img = torch.cat([img, img_table], dim=1)

    return img


def draw_bboxs(img, bboxs, color=(255, 255, 255), line_width=2):
    # img: 3xHxW, bboxs: Nx[x0, y0, x1, y1]
    for bbox in bboxs:
        img = draw_bbox(img=img, bbox=bbox, color=color, line_width=line_width)
    return img


def draw_bbox(img, bbox, color=(255, 255, 255), line_width=2):
    # img: 3xHxW, bbox: [x0, y0, x1, y1]

    device = img.device

    bbox = bbox.detach().cpu().numpy()
    bbox = np.round(bbox).astype(np.int32)
    img = tensor_to_cv_img(img.clone())
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = img.astype(np.float32)
    cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, line_width)
    img = torch.from_numpy(img).permute(2, 0, 1)
    img = img.to(device=device, dtype=torch.uint8)
    return img


def get_bboxs_from_masks(masks):
    # masks: ...xHxW
    # bboxs: ...x4
    H, W = masks.shape[-2:]
    masks_batches = masks.shape[:-2]
    masks = masks.reshape(-1, H, W)
    from torchvision.ops import masks_to_boxes

    try:
        boxes = masks_to_boxes(masks > 0.5).long()
    except Exception:
        boxes = torch.ones((masks.shape[0], 4)).long()
        boxes[:, 0] = 0
        boxes[:, 1] = 0
        boxes[:, 2] = W - 1
        boxes[:, 3] = H - 1
    boxes = boxes.reshape(*masks_batches, 4)
    return boxes


def draw_lines(img, lines, colors=None, thickness=2):
    # lines: K x 2 x 2
    K = lines.shape[0]

    device = img.device
    img = tensor_to_cv_img(img.clone())
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)

    if colors is None:
        colors = get_colors(K) * 1.0
    elif isinstance(colors, tuple) or isinstance(colors, list):
        colors = torch.from_numpy(np.tile(np.array(colors), reps=(K, 1)) / 255)
    colors = (colors.detach().cpu().numpy() * 255).astype(np.uint8)

    for k in range(K):
        cv2.line(
            img,
            pt1=(int(lines[k, 0, 0].item()), int(lines[k, 0, 1].item())),
            pt2=(int(lines[k, 1, 0].item()), int(lines[k, 1, 1].item())),
            color=(
                colors[k, 0].item(),
                colors[k, 1].item(),
                colors[k, 2].item(),
            ),
            thickness=thickness,
        )

    # img = img / 255.0
    img = torch.from_numpy(img).permute(2, 0, 1)
    img = img.to(device=device, dtype=torch.uint8)
    return img

    # cv2.line(image, start_point, end_point, color, thickness)


def draw_pixels(img, pxls, colors=None, radius_in=3, radius_out=5):
    # pxls: K x 2
    K, _ = pxls.shape

    device = img.device
    img = tensor_to_cv_img(img.clone())
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)

    if colors is None:
        colors = get_colors(K) * 1.0
    elif isinstance(colors, tuple) or isinstance(colors, list):
        colors = torch.from_numpy(np.tile(np.array(colors), reps=(K, 1)) / 255)
    colors = (colors.detach().cpu().numpy() * 255).astype(np.uint8)

    # img = cv2.circle(img.copy(), (240, 240), 5, (255, 255, 255), -1)
    for k in range(K):
        cv2.circle(
            img,
            (int(pxls[k, 0].item()), int(pxls[k, 1].item())),
            radius_out,
            (
                colors[k, 0].item(),
                colors[k, 1].item(),
                colors[k, 2].item(),
            ),
            -1,
        )
        if radius_in > 0:
            cv2.circle(
                img,
                (int(pxls[k, 0].item()), int(pxls[k, 1].item())),
                radius_in,
                (255, 255, 255),
                -1,
            )

    # img = img / 255.0
    img = torch.from_numpy(img).permute(2, 0, 1)
    img = img.to(device=device, dtype=torch.uint8)
    return img


def floats2colors(colors_floats, color_map=cv2.COLORMAP_VIRIDIS):
    # colors_floats: K,
    torch_colors = (
        torch.from_numpy(
            cv2.applyColorMap(
                tensor_to_cv_img(colors_floats.repeat(1, 1, 1)),
                color_map,
            ),
        )
        / 255.0
    ).flip(dims=(-1,))
    return torch_colors[0]


def get_colors(
    K,
    device=None,
    last_white=False,
    last_white_grey=False,
    first_white=False,
    K_rel=None,
    color_map=cv2.COLORMAP_HSV,  # jet, winter, cool ,magma, viridis, twilight, twilight shifted, cividis
    randperm=False,
):
    if last_white_grey:
        K = K - 2
        color_grey = 0.7 * torch.ones(size=(1, 3))
        color_white = torch.ones(size=(1, 3))
    elif last_white or first_white:
        K = K - 1
        color_white = torch.ones(size=(1, 3))

    if K > 0:
        if K_rel is None:
            colors_floats = (
                torch.arange(K).repeat(1, 1, 1).type(torch.float32) + 1.0
            ) / (K + 1)
        else:
            alpha_rel = 0.8
            colors_rel_floats = (
                torch.arange(K_rel).repeat(1, 1, 1).type(torch.float32) + 1.0
            ) / (K_rel + 1)
            colors_not_rel_floats = (
                torch.arange(K - K_rel).repeat(1, 1, 1).type(torch.float32) + 1.0
            ) / (K - K_rel + 1)
            colors_floats = torch.cat(
                (
                    colors_rel_floats * alpha_rel,
                    colors_rel_floats[:, :, -1:] * alpha_rel
                    + (1.0 - alpha_rel) * colors_not_rel_floats,
                ),
                dim=2,
            )
        torch_colors = (
            torch.from_numpy(
                cv2.applyColorMap(
                    tensor_to_cv_img(colors_floats),
                    color_map,
                ),
            )
            / 255.0
        )

        torch_colors = torch_colors[0]
    else:
        torch_colors = torch.ones((0, 3))

    if last_white_grey:
        torch_colors = torch.cat((torch_colors, color_grey, color_white), dim=0)
    elif last_white:
        torch_colors = torch.cat((torch_colors, color_white), dim=0)
    elif first_white:
        torch_colors = torch.cat((color_white, torch_colors), dim=0)

    if device is not None:
        torch_colors = torch_colors.to(device)

    if randperm:
        torch_colors = torch_colors[torch.randperm(len(torch_colors))]
    # K x 3
    return torch_colors


def draw_text_as_img(H: int, W: int, text: str, fontScale=1.0, lineThickness: int = 2):
    img = torch.zeros(size=(3, H, W))
    return draw_text_in_rgb(
        img,
        text=text,
        fontScale=fontScale,
        lineThickness=lineThickness,
    )


def draw_text_in_rgb(
    img,
    text="title0",
    fontScale=1.0,
    lineThickness: int = 2,
    fontColor=(255, 255, 255),
    leftTopCornerOfText=(10, 50),
):
    # 3xHxW
    _, H, W = img.shape
    device = img.device
    dtype = img.dtype

    img = tensor_to_cv_img(img.clone())
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)

    font = cv2.FONT_HERSHEY_SIMPLEX

    for i, line in enumerate(text.split("\n")):
        gap = cv2.getTextSize(line, font, fontScale, lineThickness)[0][1] + 5
        topLeftCornerOfLine = (leftTopCornerOfText[0], leftTopCornerOfText[1] + gap * i)
        if (
            isinstance(fontColor[0], list)
            or isinstance(fontColor[0], tuple)
            or isinstance(fontColor[0], torch.Tensor)
        ):
            fontColorLine = fontColor[i]
            if isinstance(fontColorLine, torch.Tensor):
                fontColorLine = fontColorLine.tolist()
        else:
            fontColorLine = fontColor
        cv2.putText(
            img,
            line,
            topLeftCornerOfLine,
            font,
            fontScale,
            fontColorLine,
            lineThickness,
        )

    img = img / 255.0
    img = torch.from_numpy(img).permute(2, 0, 1)
    if dtype == torch.uint8:
        img = img * 255.0
    img = img.to(device=device, dtype=dtype)

    return img

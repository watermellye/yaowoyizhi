from ctypes import resize
from hoshino import Service, aiorequests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from hoshino.util import pic2b64
from hoshino.typing import *
import re
import base64
import os

sv = Service('套娃')


def img_gen(inp, word1='要我一直', word2=f'吗'):
    ori = inp.size[0]

    # 输入图
    le = len(word1) + len(word2) + 1
    word_y = 150

    inp_x = le * 100
    ori /= inp_x
    inp_y = int(inp_x * inp.size[1] / inp.size[0])
    inp = inp.resize((inp_x, inp_y), Image.ANTIALIAS)

    # 输出图
    outp_x = inp_x
    outp_y = inp_y + word_y
    outp = Image.new('RGBA', (outp_x, outp_y), (255, 255, 255, 255))
    outp.paste(inp, (0, 0))

    # 贴字
    font = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'msyh.ttc'), 100)
    outp_draw = ImageDraw.Draw(outp)
    outp_draw.text((0, inp_y), word1, (0, 0, 0, 255), font)
    outp_draw.text((int(outp_x / le * (le - len(word2))), inp_y), word2, (0, 0, 0, 255), font)

    # 小图长宽
    outp_small_x = outp_x
    outp_small_y = outp_y
    # 小图位于输出图的方位
    ratio_x = (len(word1) + 0.5) / le
    ratio_y = (outp_y - word_y / 2) / outp_y
    # 小图起始
    last_x = 0
    last_y = 0
    while True:
        # 小图中心坐标
        outp_small_cen_x = int(last_x + outp_small_x * ratio_x)
        outp_small_cen_y = int(last_y + outp_small_y * ratio_y)
        # print(f"outp_small_cen=({outp_small_cen_x},{outp_small_cen_y})")

        outp_small_x = int(outp_small_x / le)
        outp_small_y = int(outp_small_y / le)
        if outp_small_y > outp_small_x:
            outp_small_x = int(outp_small_x / (outp_y / outp_x))
            outp_small_y = int(outp_small_y / (outp_y / outp_x))
        if min(outp_small_x, outp_small_y) < 3:
            break
        outp_small = outp.resize((outp_small_x, outp_small_y), Image.ANTIALIAS)
        # print(f"outp_small=({outp_small_x},{outp_small_y})")

        # 小图左上角坐标
        outp_small_cor_x = int(outp_small_cen_x - outp_small_x / 2)
        outp_small_cor_y = int(outp_small_cen_y - outp_small_y / 2)
        # print(f"outp_small_cor=({outp_small_cor_x},{outp_small_cor_y})\n")

        outp.paste(outp_small, (outp_small_cor_x, outp_small_cor_y))

        last_x = outp_small_cor_x
        last_y = outp_small_cor_y

    outp = outp.resize((int(outp_x * ori), int(outp_y * ori)), Image.ANTIALIAS)
    return outp


async def get_pic(bot, ev):
    match = re.search(r"\[CQ:image,file=(.*),url=(.*)\]", str(ev.message))
    if not match:
        return
    resp = await aiorequests.get(match.group(2))
    resp_cont = await resp.content
    pic = Image.open(BytesIO(resp_cont)).convert("RGBA")
    return pic


async def send(bot, ev, pic):
    buf = BytesIO()
    img = pic.convert('RGB')
    img.save(buf, format='JPEG')
    base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
    await bot.send(ev, f'[CQ:image,file={base64_str}]')


@sv.on_prefix(('要我一直'))
async def ywyz(bot, ev):
    pic = await get_pic(bot, ev)
    if pic == None:
        return
    pic = img_gen(pic)
    await send(bot, ev, pic)


@sv.on_prefix(('套娃'))
async def ywyz(bot, ev):
    pic = await get_pic(bot, ev)
    if pic == None:
        return
    text = ev.message.extract_plain_text().strip().split(' ')
    text = list(filter(lambda x: x != "", text))
    print(text)
    if len(text) == 0:
        pic = img_gen(pic)
    elif len(text) >= 2:
        pic = img_gen(pic, text[0], text[1])
    else:
        pic = img_gen(pic, text[0], "")
    await send(bot, ev, pic)

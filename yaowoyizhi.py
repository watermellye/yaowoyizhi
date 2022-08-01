import os
import re
import requests
from PIL import ImageDraw, ImageFont

from hoshino import Service
from hoshino.typing import CommandSession
from ..src.utils import *

sv_help = """
要我一直 <图片>
    PS: 如果选择图片时使用at，
    将会用对应用户的头像生成
套娃 <图片> <文字1(可无)> <文字2(可无)>
""".strip()

sv = Service(
    name='要我一直',
    visible=True,
    enable_on_default=True,  # 是否默认启用
    bundle='娱乐',
    help_=sv_help
)


@sv.on_fullmatch(["帮助要我一直"])
async def bangzhu_explosion(bot, ev):
    await bot.send(ev, sv_help)


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


async def get_pic(ev):
    match = re.search(r"\[CQ:image,file=(.*),url=(.*)]", str(ev.message))
    if not match:
        return
    resp = await aiorequests.get(match.group(2))
    resp_cont = await resp.content
    pic = Image.open(BytesIO(resp_cont)).convert("RGBA")
    return pic


async def send(bot, ev, pic):
    buf = BytesIO()
    draw_img = pic.convert('RGB')
    draw_img.save(buf, format='JPEG')
    base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
    await bot.send(ev, f'[CQ:image,file={base64_str}]')


def get_qq_pic(qq):
    image = []
    api_path = f'https://q1.qlogo.cn/g?b=qq&nk={qq}&s=100'
    head = requests.get(api_path, timeout=20).content
    image.append(Image.open((BytesIO(head))))
    return image


def get_name(qq):
    url = 'https://r.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg'
    params = {'uins': qq}
    res = requests.get(url, params=params)
    res.encoding = 'GBK'
    data_match = re.search(r'\{"%s":\[".+/%s/%s/.+]}' % (qq, qq, qq), res.text)
    if data_match:
        j_str = data_match.string
        j_str = j_str.split("portraitCallBack")[1].strip("(").strip(")")
        return json.loads(j_str)[qq][-2]
    else:
        return '神秘用户'


img = {}
send_times = {}


@sv.on_command('要我一直')
async def ywyz(session: CommandSession):
    event = session.ctx
    uid = event['user_id']
    if uid not in img:
        img[uid] = []
    if uid not in send_times:
        send_times[uid] = 0
    msg = event.message
    rule = re.compile(r"^\[CQ:image.+$")

    qq_head = None
    qq_rule = re.compile(r"^\[CQ:at,qq=\d+]")
    if re.match(qq_rule, event.raw_message):
        qq = re.findall(r"\d+", event.raw_message)
        qq_head = get_qq_pic(qq[0])

    if re.match(rule, str(msg)):
        image = await save_img(get_all_img_url(event))
        img[uid].extend(image)
    elif qq_head is not None:
        img[uid].extend(qq_head)
    else:
        send_times[uid] += 1
    if send_times[uid] >= 3:
        img[uid] = []
        send_times[uid] = 0
        await session.finish('过多次未发送图片，已自动停止')

    if len(img[uid]) == 0:
        session.pause('请发送图片')
    elif len(img[uid]) >= 1:
        pic = img[uid][0]
        pic = pic.resize((pic.width * 2, pic.height * 2), Image.ANTIALIAS)
        pic = img_gen(pic)
        basic_path = os.path.join(os.path.dirname(__file__), 'img')
        out_path = os.path.join(basic_path, "ywyz.png")
        pic.save(out_path)
        msg = f'[CQ:image,file=file:///{out_path}]'
        img[uid] = []
        send_times[uid] = 0
        await session.finish(msg)


@sv.on_command('套娃')
async def summon_trap(session: CommandSession):
    event = session.ctx
    uid = event['user_id']
    if uid not in img:
        img[uid] = []
    if uid not in send_times:
        send_times[uid] = 0
    msg = event.message
    rule = re.compile(r"^\[CQ:image.+$")

    qq_head = None
    qq_rule = re.compile(r"^\[CQ:at,qq=\d+]")
    if re.match(qq_rule, event.raw_message):
        qq = re.findall(r"\d+", event.raw_message)
        qq_head = get_qq_pic(qq[0])

    if re.match(rule, str(msg)) and len(img[uid]) == 0:
        image = await save_img(get_all_img_url(event))
        img[uid].extend(image)
    elif qq_head is not None and len(img[uid]) == 0:
        img[uid].extend(qq_head)
    elif len(img[uid]) == 1 and not re.match(rule, str(msg)):
        img[uid].extend(msg)
    else:
        send_times[uid] += 1
    if send_times[uid] >= 3:
        img[uid] = []
        send_times[uid] = 0
        await session.finish('过多次未发送图片，已自动停止')

    if len(img[uid]) == 0:
        session.pause('请发送图片')
    elif len(img[uid]) == 1:
        session.pause('请发送信息，"None"代表不自定义文字')
    elif len(img[uid]) >= 2:
        bg = img[uid][0]
        text = img[uid][1].data["text"].split(" ")
        pic = bg.resize((bg.width * 2, bg.height * 2), Image.ANTIALIAS)
        rule = re.compile(r"[nN][oO][nN][eE]")
        if re.match(rule, text[0]):
            pic = img_gen(pic)
        elif len(text) >= 2:
            pic = img_gen(pic, text[0], text[1])
        else:
            pic = img_gen(pic, text[0], "")

        basic_path = os.path.join(os.path.dirname(__file__), 'img')
        out_path = os.path.join(basic_path, "taowa.png")
        pic.save(out_path)
        msg = f'[CQ:image,file=file:///{out_path}]'
        img[uid] = []
        send_times[uid] = 0
        await session.finish(msg)

# from .core import *
from shutil import copyfile
from turco import package_directory
from .core import MTurkHelper
import argparse
import json
import os

""" ============
|   Helpers   
============ """


def load_args(path):
    default_args = os.path.join(path, "default_args.json")

    if not os.path.exists(default_args):
        raise Exception("{0} does not exist!".format(default_args))

    with open(default_args, "r") as f:
        args = json.load(f)
    return args


""" ============
|   Commands   
============ """


def init():
    parser = argparse.ArgumentParser(prog='init')
    parser.add_argument('-p', help='path to create the stub')
    args = parser.parse_args()
    path = args.p

    if not os.path.exists(path):
        os.makedirs(path)
    else:
        raise Exception("Directory already exists.")
    src = os.path.join(path, "src/")
    xml = os.path.join(path, "xml/")
    out = os.path.join(path, "out/")

    if not os.path.exists(src):
        os.makedirs(src)

    if not os.path.exists(xml):
        os.makedirs(xml)

    if not os.path.exists(out):
        os.makedirs(out)

    stub = os.path.join(package_directory, "stub/")

    config_src, config_dst = os.path.join(stub, "config.json"), \
                             os.path.join(path, "config.json")

    secrets_src, secrets_dst = os.path.join(stub, "secrets.json"), \
                               os.path.join(path, "secrets.json")

    template_src, template_dst = os.path.join(stub, "template.html"), \
                                 os.path.join(path, "template.html")

    log_dst = os.path.join(path, "log.txt")

    copyfile(config_src, config_dst)
    copyfile(secrets_src, secrets_dst)
    copyfile(template_src, template_dst)

    default_args = {
        "pay_real_money": False,
        "config_path": os.path.abspath(config_dst),
        "secrets_path": os.path.abspath(secrets_dst),
        "template_path": os.path.abspath(template_dst),
        "logs_path": os.path.abspath(log_dst),
        "src_folder_path": os.path.abspath(src),
        "xml_folder_path": os.path.abspath(xml),
        "out_folder_path": os.path.abspath(out),
        "control_qualifications_path": None,
        "qualification_folder_path": None,
        "queue_url": None,
        "xml": "<HTMLQuestion " +
               "xmlns=\"http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/" +
               "HTMLQuestion.xsd\"><HTMLContent><![CDATA[{0}]]></HTMLContent><FrameHeight>2000</FrameHeight>" +
               "</HTMLQuestion>"
    }

    with open(os.path.join(path, "default_args.json"), "w") as f:
        json.dump(default_args, f)

    with open(os.path.join(stub, "q1.json"), "r") as f:
        q1 = json.load(f)
    with open(os.path.join(src, "q1.json"), "w") as f:
        json.dump(q1, f)


def create_questions():
    parser = argparse.ArgumentParser(prog='init')
    parser.add_argument('-p', help='path to create the stub')
    args = parser.parse_args()
    path = args.p
    default_args = load_args(path)
    mturk_helper = MTurkHelper(**default_args)
    mturk_helper.create_questions()


def publish_questions():
    parser = argparse.ArgumentParser(prog='init')
    parser.add_argument('-p', help='path to create the stub')
    parser.add_argument("-pay", help="pay real money")

    args = parser.parse_args()

    path = args.p
    pay = args.pay

    if pay is not None:
        args["pay_real_money"] = True

    default_args = load_args(path)
    mturk_helper = MTurkHelper(**default_args)
    mturk_helper.publish_questions()


def retrieve_questions():
    parser = argparse.ArgumentParser(prog='init')
    parser.add_argument('-p', help='path to create the stub')
    parser.add_argument("-pay", help="pay real money")
    parser.add_argument("-alternames", help="alter names, splitting hits on the web interface")

    args = parser.parse_args()

    path = args.p
    pay = args.pay
    alter_names = args.alternames

    if pay is not None:
        args["pay_real_money"] = True

    if alter_names is not None:
        alter_names = True
    else:
        alter_names = False

    default_args = load_args(path)
    mturk_helper = MTurkHelper(**default_args)
    mturk_helper.get_replies(alter_names=alter_names)

import json
import linecache
import logging
import sys

from flask import jsonify

from error_code import ErrorElement


def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in allowed_extensions


def json_response(data=None, msg='Success', code='E000'):
    return jsonify(msg=msg, data=data, code=code)


def json_response_element(error_element: ErrorElement):
    return json_response(msg=error_element.msg, code=error_element.code)


def print_exception(use_logger=False, exit=False):
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    line = line.strip()

    msg = 'EXCEPTION IN ({}, LINE: {}, CODE: {}): {} {}'.format(filename, lineno, line, exc_type, exc_obj)

    if use_logger:
        logging.error(msg)
    else:
        print(msg)

    if exit:
        sys.exit(1)

    return msg


def get_sorted_keys(dict_obj, reverse=True):
    """

    :param dict_obj:
    :param reverse: True: descending order, False: ascending order
    :return: list of keys
    """
    return list(dict(sorted(dict_obj.items(), key=lambda item: item[1], reverse=reverse)).keys())


def get_sorted_dict(dict_obj, reverse=True):
    """

    :param dict_obj:
    :param reverse: True: descending order, False: ascending order
    :return: sorted dict
    """
    return dict(sorted(dict_obj.items(), key=lambda item: item[1], reverse=reverse))


def get_dict_items(dict_obj):
    """
    Dictionary의 value들을 list 형태로 합치는 함수
    :param dict_obj:
    :return:
    """
    output = []
    for key, values in dict_obj.items():
        output.extend(values)

    return output


def load_json(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data


def save_to_json(data, filename='data.json'):
    if filename[-4:] != 'json':
        filename += '.json'

    with open(f'{filename}', 'w', encoding='utf-8') as fw:
        json.dump(data, fw, indent=4, ensure_ascii=False)


def read_file(file):
    lines = []
    with open(file, 'r', encoding='utf-8') as f:
        for line in f:
            lines.append(line.strip())

    return lines
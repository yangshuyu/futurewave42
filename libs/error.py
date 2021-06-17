from webargs.flaskparser import parser, abort

from libs.interface_tips import InterfaceTips


# @parser.error_handler
# def handle_error(e, req, schema, status_code, headers):
#     if hasattr(e, 'kwargs') and e.kwargs.get('error_info'):
#         error(e.kwargs.get('error_info'), errors=e.messages)
#     error(errors=e.messages)
#
#
# def error(params=None, code=422, message='不合法的请求', errors=None):
#     params['message'] = message
#     params['errcode'] = code
#     if errors:
#         params['errors'] = errors
#
#     abort(code, **params)


@parser.error_handler
def handler_request_parsing_error(e, req, schema, status_code, headers):
    if hasattr(e, "kwargs") and e.kwargs.get("error_info"):
        error(e.kwargs.get("error_info"), errors=e.messages)
    error(errors=e.messages)


def error(error_info=InterfaceTips.INVALID_REQUEST, errors=None):
    http_code, error_code, error_msg = error_info.value
    params = {"message": error_msg, "code": error_code}
    if errors:
        params["errors"] = errors

    abort(http_code, **params)


def dynamic_error(params=None, code=422, message='不合法的请求', errors=None):
    params['message'] = message
    params['errcode'] = code
    if errors:
        params['errors'] = errors

    abort(code, **params)

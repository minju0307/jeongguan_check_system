class ErrorElement():
    code = int()
    msg = str()

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg


class ErrorCode():
    UNKNOWN_ERROR = ErrorElement(100, 'Unknown error')
    NO_SERVER_RESPONSE = ErrorElement(101, 'No server response')
    INVALID_PARAMETER = ErrorElement(102, 'Invalid parameter')

    ASR_SERVER_ERROR = ErrorElement(110, 'Speech recognizer error')
    SUMMARY_SERVER_ERROR = ErrorElement(120, 'Summary recognizer error')
    AUTUMN_SEVERITY_SERVER_ERROR = ErrorElement(130, 'Autumn severity recognizer error')
    DDK_SEVERITY_SERVER_ERROR = ErrorElement(140, 'DDK severity recognizer error')

    NOT_EXIST_UID = ErrorElement(150, 'uid does not exist')

    INVALID_DOCUMENT = ErrorElement(160, 'Invalid document')

    SUCCESS = ErrorElement(200, 'Success')
    TIMEOUT = ErrorElement(300, 'Timeout')

    NOT_SUPPORT_API = ErrorElement(400, 'Not support API')

    NO_FILE_PART = ErrorElement(500, 'No file part')
    NO_SELECTED_FILE = ErrorElement(501, 'No selected file')
    NOT_ALLOWED_FILE_EXTENSION = ErrorElement(502, 'Not allowed file extension')
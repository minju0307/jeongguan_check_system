class ErrorElement():
    code = int()
    msg = str()

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg


class ErrorCode():
    UNKNOWN_ERROR = ErrorElement(100, 'Unknown error')
    NO_SERVER_RESPONSE = ErrorElement(101, 'No server response')

    ASR_SERVER_ERROR = ErrorElement(110, 'Speech recognizer error')
    SUMMARY_SERVER_ERROR = ErrorElement(120, 'Summary recognizer error')
    AUTUMN_SEVERITY_SERVER_ERROR = ErrorElement(130, 'Autumn severity recognizer error')
    DDK_SEVERITY_SERVER_ERROR = ErrorElement(140, 'DDK severity recognizer error')

    NO_AGE_ERROR = ErrorElement(150, 'No age error')
    NO_GENDER_ERROR = ErrorElement(151, 'No gender error')

    SUCCESS = ErrorElement(200, 'Success')
    TIMEOUT = ErrorElement(300, 'Timeout')

    NOT_SUPPORT_API = ErrorElement(400, 'Not support API')

    NO_FILE_PART = ErrorElement(500, 'No file part')
    NO_SELECTED_FILE = ErrorElement(501, 'No selected file')
    NOT_ALLOWED_FILE_EXTENSION = ErrorElement(502, 'Not allowed file extension')
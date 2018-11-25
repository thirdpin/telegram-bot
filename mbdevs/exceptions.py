class ComDeviceNotFound(IOError):
    pass

class CannotReadARegisterValue(Exception):
    def __init__(self, reg):
        msg = "Cannot a value read {} register".format(reg.name)
        super().__init__(msg)
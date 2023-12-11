class User:
    def __init__(self, phone_number, api_id, api_hash, proxy, loop, id=None):
        self.phoneNumber = phone_number
        self.proxy = proxy
        self.id = id
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.loop = loop
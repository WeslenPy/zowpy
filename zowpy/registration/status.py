

class Status:

    @property
    def banned(cls):
        return "blocked".upper()

    @property
    def unbanned(cls):
        return  "UNBANNED".upper()
    
    @property
    def unblocked(cls):
        return  "incorrect".upper()
    
    
    @property
    def too_many(cls):
        return  "too_many".upper()
    
    
    
    @property
    def unavailable(cls):
        return  "temporarily_unavailable".upper()
    
    @property
    def review(cls):
        return "IN_REVIEW".upper()    
    
    @property
    def fail(cls):
        return "FAIL".upper()    
    
    @property
    def success(cls):
        return "ok".upper()   
    
     
    @property
    def sent(cls):
        return "sent".upper()    
    
    @property
    def permanently(cls):
        return "BANNED".upper()
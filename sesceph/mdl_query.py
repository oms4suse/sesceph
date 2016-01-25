class _mdl_query():
    """
    This is for querying the model with common queries,
    that are internal.
    """
    def __init__(self, model):
        self.model = model

    def mon_is(self):
        if self.model.hostname == None:
            raise Error("Programming error: Hostname not detected")
        for hostname, addr in self.model.mon_members:
            if hostname == self.model.hostname:
                return True
        return False

    def mon_quorum(self):
        """
        Present the monitor status
        """
        if (None == self.model.mon_status):
            return False
        name = self.model.mon_status.get("name")
        outside_quorum = self.model.mon_status.get("outside_quorum")
        if name in outside_quorum:
            return False
        return True

from sqlalchemy import asc, desc

from ..models.models import SampleItem


class FastAPIFeatures:
    def __init__(self, query, params):
        self.query = query
        self.params = params

    def sort(self):
        sort = self.params.get("sort")
        order = self.params.get("order")

        if sort:
            if order == "desc":
                self.query = self.query.order_by(desc(getattr(SampleItem, sort)))
            else:
                self.query = self.query.order_by(asc(getattr(SampleItem, sort)))

        return self

    def paginate(self):
        page = int(self.params.get("page", 0))
        limit = int(self.params.get("limit", 100))

        self.query = self.query.offset(page * limit).limit(limit)
        return self

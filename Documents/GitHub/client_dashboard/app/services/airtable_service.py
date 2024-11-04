import airtable

class AirtableService:
    def __init__(self, base_id, api_key, table_name):
        self.client = airtable.Airtable(base_id, table_name, api_key)

    def fetch_records(self):
        return self.client.get_all()

    def add_record(self, record):
        return self.client.insert(record)

    def update_record(self, record_id, fields):
        return self.client.update(record_id, fields)

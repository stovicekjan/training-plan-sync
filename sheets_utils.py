from __future__ import annotations

import datetime
import pprint
import re
from dateutil import relativedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from calendar_utils import TrainingEvent

TRAINING_PLAN_PREFIX = 'Tréninkový plán - '
MY_SPREADSHEET_ID = "1HSeHKDTbP9bDI5D127TcADhAONSrH0j77avNJu1nx7E"
MONTHS_CZ2EN = {
    "leden": "1", "únor": "2", "březen": "3", "duben": "4", "květen": "5", "červen": "6",
    "červenec": "7", "srpen": "8", "září": "9", "říjen": "10", "listopad": "11", "prosinec": "12",
}

HEADER_DATE = "Datum"
HEADER_TRAINING_CONTENT = "Náplň tréninku"
HEADER_TRAINING_TIME = "Skutečnost čas"
HEADER_TRAINING_DISTANCE = "Skutečnost km"

TEXTS_FREE_DAY = ["volno", "-", "nemoc"]


class Sheet:
    """
    A single sheet within a spreadsheet
    """
    def __init__(self, name, sheet_id):
        self.name = name
        self.sheet_id = sheet_id

    def print(self):
        print(f'Sheet {self.sheet_id}: {self.name}')


class SheetList(list):
    def print(self):
        for sheet in self:
            print(sheet.sheet_id, sheet.name)

    def filter_current_sheets(self) -> SheetList:
        """
        Filter the sheets that can contain trainings relevant to the current month -> the previous one, the current one
        and the next one
        :return: filtered list
        """
        rgx = re.compile(r"%s(.*)(\d{4})" % TRAINING_PLAN_PREFIX)  # pattern: TRAINING_PLAN_PREFIX month_cz yyyy
        filtered_list = SheetList()

        for sheet in self:
            m = rgx.match(sheet.name)
            if m:
                sheet_month = int(MONTHS_CZ2EN[m.group(1).strip()])
                sheet_year = int(m.group(2).strip())
                now = datetime.datetime.now()
                next_month = now + relativedelta.relativedelta(months=1)
                prev_month = now + relativedelta.relativedelta(months=-1)
                if (sheet_month == now.month and sheet_year == now.year) or \
                        (sheet_month == next_month.month and sheet_year == next_month.year) or \
                        (sheet_month == prev_month.month and sheet_year == prev_month.year):
                    filtered_list.append(sheet)

        return filtered_list


class SheetsUtils:
    def __init__(self, creds):
        try:
            self.service = build('sheets', 'v4', credentials=creds)
        except HttpError as e:
            print(f'An Error occurred while connecting to Google Sheets: {e}')

    def get_sheet_list(self) -> SheetList:
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=MY_SPREADSHEET_ID).execute()
        sheets = spreadsheet.get('sheets')
        sheet_list = SheetList()
        for sheet in sheets:
            sheet_list.append(Sheet(sheet['properties']['title'], sheet['properties']['sheetId']))
        return sheet_list

    def find_column(self, column_name: str, row: list) -> int:
        """
        Find the column based on its name
        :param column_name: name of the column (should be located in the 1st row)
        :param row: the values in the 1st row
        :return: column index
        """
        i = 0
        for value in row:
            if value.lower() == column_name.lower():
                return i
            i += 1

        raise ValueError(f"Could not find value {column_name} in the first row.")

    def read_sheet_values(self, sheet_list: SheetList):
        trainings_list = []
        try:
            for sheet in sheet_list:
                sheet_name = sheet.name
                response = self.service.spreadsheets()\
                    .values()\
                    .get(spreadsheetId=MY_SPREADSHEET_ID, range=sheet_name, valueRenderOption="UNFORMATTED_VALUE", dateTimeRenderOption="SERIAL_NUMBER").execute()
                values = response.get('values', [])

                if not values:
                    print('No data found.')
                    return []

                print(f'Reading values from {sheet_name}')
                idx_date = self.find_column(HEADER_DATE, values[0])
                idx_training_content = self.find_column(HEADER_TRAINING_CONTENT, values[0])
                # print(f"Sheet {sheet_name}: Columns {idx_date} and {idx_training_content}")
                for row in values:
                    if len(row) > idx_training_content and str(row[idx_date]).isdigit():
                        training_date = datetime.datetime(1900, 1, 1) + relativedelta.relativedelta(days=int(row[idx_date]) - 2)  # probably, Google Sheets handle leap years incorrectly
                        training_content = row[idx_training_content]
                        if training_date.date() >= datetime.datetime.today().date() and training_content.lower() not in TEXTS_FREE_DAY:
                            print(training_date.date(), training_content)
                            trainings_list.append(TrainingEvent(training_date, training_content))

            return trainings_list

        except HttpError as err:
            print(err)


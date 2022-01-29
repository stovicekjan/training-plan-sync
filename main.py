from __future__ import print_function

from auth import Auth
from calendar_utils import CalendarUtils
from sheets_utils import SheetsUtils


def main():
    credentials = Auth.authenticate()
    calendar = CalendarUtils(credentials)

    sheets_service = SheetsUtils(credentials)

    sheets_list = sheets_service.get_sheet_list()
    filtered_sheet_list = sheets_list.filter_current_sheets()
    filtered_sheet_list.print()

    trainings_list = sheets_service.read_sheet_values(filtered_sheet_list)

    calendar.sync(trainings_list)

    # calendar.list_existing_events()
    # event = {
    #         "summary": "test haha",
    #         "description": "fdfdfsd",
    #         "start": {
    #             "date": '2022-01-28'
    #         },
    #         "end": {
    #             "date": '2022-01-29'
    #         }
    #     }
    # calendar.service.events().insert(calendarId='primary', body=event).execute()


if __name__ == '__main__':
    main()

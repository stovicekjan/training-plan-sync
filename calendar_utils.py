import datetime
import json
import pprint
from typing import List

from dateutil import relativedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

EVENT_DESCRIPTION = "run#0a77ef92f6"    # this pseudo-unique hex string should be inserted as an event type to identify events created by this app


class TrainingEvent:
    def __init__(self, training_date: datetime, training_content: str):
        self.training_date = training_date
        date_end = training_date + relativedelta.relativedelta(days=1)
        self.training_contant = training_content
        self.json_payload = {
            "summary": training_content,
            "description": EVENT_DESCRIPTION,
            "start": {
                "date": training_date.date().isoformat()
            },
            "end": {
                "date": date_end.date().isoformat()
            }
        }

    def __str__(self):
        return f"{self.training_date}: {self.training_contant}"


class CalendarUtils:
    def __init__(self, creds):
        try:
            self.service = build('calendar', 'v3', credentials=creds)
        except HttpError as error:
            print(f'An error occurred: {error}')

    def write(self, training: TrainingEvent):
        try:
            event = self.service.events().insert(calendarId='primary', body=training.json_payload).execute()
            print(f"Created event: {event.get('htmlLink')}")
        except HttpError as error:
            print(f'An error while inserting the event: {error}')

    def overwrite(self, training: TrainingEvent, orig_event: dict):
        try:
            orig_event_id = orig_event.get('id')
            event = self.service.events().update(calendarId='primary', body=training.json_payload, eventId=orig_event_id).execute()
            print(f"Updated event: {event.get('htmlLink')}")
        except HttpError as error:
            print(f'An error while updating the event: {error}')

    def delete(self, event: dict):
        try:
            event_id = event.get('id')
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f"Deleted event: {event.get('start').get('date')} - {event.get('summary')}")
        except HttpError as error:
            print(f'An error while updating the event: {error}')

    def sync(self, trainings_list: List[TrainingEvent]):
        existing_events = self.list_existing_events()
        synced_events = []

        for event in existing_events:
            print(f"=========================")
            print(f"Existing event: {event.get('start').get('date')}")
            # modify trainings that were modified in the google sheet
            for training in trainings_list:
                if event.get('start').get('date') == training.json_payload.get('start').get('date') and event.get('summary') == training.training_contant:
                    # the same training already exists -> skip it and don't check that one again
                    print(f"Unchanged training: {training.training_date} - {training.training_contant}")
                    trainings_list.remove(training)
                    synced_events.append(event)
                    break
                elif event.get('start').get('date') == training.json_payload.get('start').get('date') and event.get('summary') != training.training_contant:
                    # a different training exists for this day (it was modified) -> overwrite it
                    print(f"Modified training: {training.training_date} - {training.training_contant} -> OVERWRITE")
                    self.overwrite(training, event)
                    trainings_list.remove(training)
                    synced_events.append(event)
                    break

        events_to_delete = [e for e in existing_events if e not in synced_events]
        for event in events_to_delete:
            # there is an event in the calendar, but not in training plan -> delete it
            print(f"Missing training for {event.get('start').get('date')}: -> DELETE")
            self.delete(event)
            # FIXME delete the remaining existing events now

        # add new trainings from the google sheet
        for training in trainings_list:
            print(f"Adding training: {training}")
            self.write(training)

    def list_existing_events(self) -> List[dict]:
        """
        Lists events created by this application (they possess the special EVENT_DESCRIPTION attribute)
        :return: list of events created by this application
        """
        now = datetime.datetime.now() + relativedelta.relativedelta(days=-1)   # FIXME
        today = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=0, second=0)
        today_formatted = today.isoformat() + 'Z'
        events_result = self.service.events().list(calendarId='primary', timeMin=today_formatted,
                                              maxResults=30, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        self.print_events(events, "All events", verbose=True)
        my_events = [event for event in events if event.get('description') == EVENT_DESCRIPTION]
        self.print_events(my_events, "Events created by this app:")
        return my_events

    def print_events(self, events: list, title: str, verbose=False):
        print(title)
        for e in events:
            if not verbose:
                print("{}\t{}\t{}\t{}".format(e.get('start').get('date'), e.get('summary'), e.get('id'), e.get('description')))
            else:
                print(e)

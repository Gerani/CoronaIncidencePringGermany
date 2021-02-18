import json
import os
from urllib import request
from datetime import datetime
from typing import Union
from argparse import ArgumentParser


class Data(object):
    def __init__(self):
        self.url_history_json = 'https://opendata.arcgis.com/datasets/6d78eb3b86ad4466a8e264aa2e32a2e4_0.geojson'
        self.url_admin_unit_json = 'https://opendata.arcgis.com/datasets/58dba7034918475cb8aaf8ad38f7e77a_0.geojson'
        self.url_actual_json = 'https://opendata.arcgis.com/datasets/c2f3c3b935a242169c6bec82e1fa573e_0.geojson'
        self.url_landkreise_json = 'https://opendata.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0.geojson'
        self.url_bundeslaender_json = 'https://opendata.arcgis.com/datasets/ef4b445a53c1406892257fe63129a8ea_0.geojson'
        self.json_file = f"{datetime.now().date()}.json"
        self._history = None
        self._admin = None
        self._actual = None
        self._landkreise = None
        self._bundeslaender = None

    @property
    def history(self):
        if self._history is not None:
            return self._history
        else:
            self._load_data()
            return self._history

    @property
    def admin(self):
        if self._admin is not None:
            return self._admin
        else:
            self._load_data()
            return self._admin

    @property
    def actual(self):
        if self._actual is not None:
            return self._actual
        else:
            self._load_data()
            return self._actual

    @property
    def landkreise(self):
        if self._landkreise is not None:
            return self._landkreise
        else:
            self._load_data()
            return self._landkreise

    @property
    def bundeslaender(self):
        if self._bundeslaender is not None:
            return self._bundeslaender
        else:
            self._load_data()
            return self._bundeslaender

    def _load_data(self):
        if os.path.isfile(self.json_file):
            self._load_from_file()
        else:
            self._load_from_internet()

    def _load_from_internet(self):
        self._history = self._get_json_url(self.url_history_json)
        self._admin = self._get_json_url(self.url_admin_unit_json)
        self._actual = self._get_json_url(self.url_actual_json)
        self._landkreise = self._get_json_url(self.url_landkreise_json)
        self._bundeslaender = self._get_json_url(self.url_bundeslaender_json)
        with open(f"{datetime.now().date()}.json", 'w') as output:
            json.dump((self._history, self._admin, self._actual, self._landkreise, self._bundeslaender), output)

    def _load_from_file(self):
        self._history, self._admin, self._actual, self._landkreise, self._bundeslaender = self._get_json_file(
            self.json_file)
        for entry in os.listdir('.'):
            if os.path.splitext(entry)[1] == '.json':
                if entry != self.json_file:
                    os.remove(entry)

    @staticmethod
    def _get_json_url(url):
        response = request.urlopen(url)
        data = response.read()
        text = data.decode('utf-8')
        return json.loads(text)

    @staticmethod
    def _get_json_file(file_name):
        with open(file_name, 'r') as infile:
            text = infile.read()
        return json.loads(text)


class Corona(object):
    def __init__(self, lk: str, corona_data: Data, inzidenz=7):
        self.lk = lk
        self.data = corona_data
        self.inzidenz = inzidenz
        self._specific_data_history = []
        self._specific_data_actual = None
        self._cleaned_data_history = {}
        self._id = None
        self._einwohnerzahl = None
        self._calculated_incidence = []

    @property
    def id(self) -> int:
        if self._id is not None:
            return self._id
        for entry in self.data.admin['features']:
            if entry['properties']['Name'] == self.lk:
                self._id = entry['properties']['AdmUnitId']
                return self._id

    @property
    def einwohnerzahl(self) -> int:
        if self._einwohnerzahl is not None:
            return self._einwohnerzahl
        for entry in self.data.landkreise['features']:
            if entry['properties']['AdmUnitId'] == self.id:
                self._einwohnerzahl = entry['properties']['EWZ']
                return self._einwohnerzahl
        for entry in self.data.bundeslaender['features']:
            if entry['properties']['AdmUnitId'] == self.id:
                self._einwohnerzahl = entry['properties']['LAN_ew_EWZ']
                return self._einwohnerzahl
        self._einwohnerzahl = 0
        for entry in self.data.bundeslaender['features']:
            self._einwohnerzahl += entry['properties']['LAN_ew_EWZ']
        return self._einwohnerzahl

    @property
    def specific_data_history(self) -> list:
        if self._specific_data_history:
            return self._specific_data_history
        for entry in self.data.history['features']:
            new_entry = entry['properties']
            if new_entry['AdmUnitId'] == self.id:
                self._specific_data_history.append(new_entry)
        return self._specific_data_history

    @property
    def specific_data_actual(self) -> dict[str, Union[int, str]]:
        if self._specific_data_actual is not None:
            return self._specific_data_actual
        else:
            for entry in self.data.actual['features']:
                new_entry = entry['properties']
                if new_entry['AdmUnitId'] == self.id:
                    self._specific_data_actual = new_entry
                    return self._specific_data_actual

    @property
    def cleaned_data_history(self) -> dict[datetime, Union[int, str]]:
        if self._cleaned_data_history:
            return self._cleaned_data_history
        for entry in self.specific_data_history:
            self._cleaned_data_history.update({self._get_right_datetime(entry['Datum']): entry['AnzFallVortag']})
        return self._cleaned_data_history

    @property
    def cleaned_data_actual(self) -> dict[datetime.date, int]:
        return {datetime.now().date(): self.specific_data_actual['AnzFallNeu']}

    @staticmethod
    def _get_right_datetime(date: str) -> datetime.date:
        return datetime.fromisoformat(date[:-1]).date()

    @property
    def combined_data(self):
        new_dict = self.cleaned_data_history
        new_dict.update(self.cleaned_data_actual)
        return new_dict

    @property
    def sorted_dates(self):
        return sorted(self.combined_data)

    @property
    def calculated_incidence(self) -> list[tuple[datetime, int]]:
        if self._calculated_incidence:
            return self._calculated_incidence
        for counter, date in enumerate(self.sorted_dates):
            illnesses = 0
            if counter > self.inzidenz:
                for i in range(0, self.inzidenz+1):
                    illnesses += self.combined_data[self.sorted_dates[counter-i]]
            self._calculated_incidence.append((date, self._calc_incidence(illnesses)))
        return self._calculated_incidence

    @property
    def calculated_incidence_dict(self) -> dict[datetime, int]:
        ret_val = {}
        for date, incidence in self.calculated_incidence:
            ret_val.update({date: incidence})
        return ret_val

    def _calc_incidence(self, illnesses):
        return round(illnesses/self.einwohnerzahl*100000, 1)

    def print_incidence(self):
        print(self.lk)
        for date, incidence in self.calculated_incidence:
            print(f'{date.date()}: {incidence}')


class PrintTable(object):
    def __init__(self, values: list[Corona]):
        self.values = values
        self.to_print = []
        self.date_padding = 12
        self.value_padding = []

    def print_table(self, last_days=None):
        self.calc_value_padding()
        self.calc_to_print(last_days)
        self.print_header()
        self.print_entries()
        self.print_footer()

    def calc_value_padding(self):
        for lk in self.values:
            self.value_padding.append(len(lk.lk))

    def print_line(self):
        to_print = '+' + self.date_padding * '-'
        for i in range(0, len(self.values)):
            to_print += '+' + '-' * self.value_padding[i]
        to_print += '+'
        print(to_print)

    def print_header(self):
        self.print_line()
        to_print = f'|{"Datum".ljust(self.date_padding, " ")}'
        for counter, entry in enumerate(self.values):
            to_print += f'|{entry.lk.ljust(self.value_padding[counter], " ")}'
        to_print += '|'
        print(to_print)
        self.print_line()

    def print_entries(self):
        to_print = '|'
        for entry in self.to_print:
            to_print = f'|{entry[0].ljust(self.date_padding, " ")}'
            for counter, value in enumerate(entry[1:]):
                to_print += f'|{value.ljust(self.value_padding[counter], " ")}'
            to_print += '|'
            print(to_print)

    def print_footer(self):
        self.print_line()

    def valid_dates(self, last_days):
        if last_days is None:
            return self.dates
        else:
            return self.dates[last_days*-1:]

    def calc_to_print(self, last_days):
        for date in self.valid_dates(last_days):
            data = []
            for lk in self.values:
                data.append(str(lk.calculated_incidence_dict[date]))
            self.to_print.append((str(date), *data))

    @property
    def dates(self):
        return self.values[0].sorted_dates


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-l', '--landkreise', required=True)
    parser.add_argument('-d', '--last_days', required=False, default=14, type=int)
    args = parser.parse_args()
    data = Data()
    lks = []
    for lk in args.landkreise.split(';'):
        lks.append(Corona(lk, data))
    table = PrintTable(lks)
    table.print_table(args.last_days)

#!/usr/bin/env python
#
# Copyright 2008 Kevin Dwyer

from pysqlite2 import dbapi2 as sqlite

if __name__ == '__main__':
    conn = sqlite.connect('mayors-money')

    curs = conn.cursor()
    curs.execute("create table cities (city_id integer, name varchar2(100), state char(2))")
    curs.execute("create table programs (program_id integer, name varchar2(100))")
    curs.execute("create table projects (project_id integer, city_id integer, description varchar2(200), num_jobs number, money number, program_id integer)")

    max_program_id = max_city_id = max_project_id = 0
    programs = {}
    cities = {}

    for line in file('dicts'):
        data = eval(line)

        city = data['City']
        state = data['State']
        desc = data['Project Description'].encode('utf-8')
        jobs = data['Jobs']
        money = data['Funding Required']
        program = data['Program']

        program_id = programs.get(program, -1)
        if program_id == -1:
            program_id = max_program_id
            programs[program] = program_id
            curs.execute("insert into programs (program_id, name) values (?, ?)", [program_id, program])
            max_program_id += 1

        city_id = cities.get((city, state), -1)
        if city_id == -1:
            city_id = max_city_id
            cities[(city, state)] = city_id
            curs.execute("insert into cities (city_id, name, state) values (?, ?, ?)", [city_id, city, state])
            max_city_id += 1

        curs.execute("insert into projects (project_id, description, num_jobs, money, program_id, city_id) values (?, ?, ?, ?, ?, ?)", [max_project_id, desc, jobs, money, program_id, city_id])
        max_project_id += 1

    conn.commit()

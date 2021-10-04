import requests, time
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime 

conn = sqlite3.connect('database.db')
Miner, Algo, Port, Link, FirstResponse = None, None, None, None, None
APIPorts = ['4003', '4002']

def TimeDelta(duration):
    if duration < 60:
        secs = str(duration)
        if len(secs) != 2:
            secs = "0" + secs

        return "00" + " Day " + "00" + " Hr " + "00" + " Min " + secs + ' Sec'
    elif duration > 59 and duration < 3600:
        mins = str(int(duration / 60))
        if len(mins) != 2:
            mins = "0" + mins 

        secs = str(duration % 60)
        if len(secs) != 2:
            secs = "0" + secs

        return  "00" + " Day " + "00" + " Hr " + mins + " Min " + secs + ' Sec'
    elif duration >= 3600 and duration < 86400:
        hrs = str(int(duration / 3600))
        if len(hrs) != 2:
            hrs = "0" + hrs

        rem = duration % 3600

        mins = str(int(rem / 60))
        if len(mins) != 2:
            mins = "0" + mins 

        secs = str(rem % 60)
        if len(secs) != 2:
            secs = "0" + secs

        return  "00" + " Day " + hrs + " Hr " + mins + " Min " + secs + ' Sec'
    else:
        day = str(int(duration / 86400))
        if len(day) != 2:
            day = "0" + day

        duration = duration % 86400
        hrs = str(int(duration / 3600))
        if len(hrs) != 2:
            hrs = "0" + hrs

        rem = duration % 3600

        mins = str(int(rem / 60))
        if len(mins) != 2:
            mins = "0" + mins 

        secs = str(rem % 60)
        if len(secs) != 2:
            secs = "0" + secs

        return  day + " Day " + hrs + " Hr " + mins + " Min " + secs + ' Sec'

def FindActive():
    global Miner, Algo, Port, Link, FirstResponse
    # Check for Miner
    for port in APIPorts:
        try:
            html_doc = requests.get('http://localhost:' + port)
        except:
            print("The port " + port + " is not active")
            continue
        print("The port " + port + " is active")
        soup = BeautifulSoup(html_doc.content, 'html.parser')
        Miner = soup.title.get_text().split(' ')[0]
        Port = port
        break

    # NBMiner - Check Algo
    if Miner == 'NBMiner':
        Link = 'http://localhost:' + Port + "/api/v1/status"
        Response = requests.get(Link)
        JSON = Response.json()
        Algo = JSON['stratum']['algorithm']
        FirstResponse = JSON

    # TREX - Check Algo
    elif Miner == 'T-Rex':
        Link = "http://localhost:" + Port + "/summary"
        Response = requests.get(Link)
        JSON = Response.json()
        Algo = JSON['algorithm']
        FirstResponse = JSON
        uuid = str(int((int(datetime.timestamp(datetime.now())) - int(FirstResponse['uptime']))/10))
        FirstResponse['uuid'] = uuid + "5"

def CreateTables():
    # Try creating TABLES
    try:
        conn.execute(
            '''
                CREATE TABLE SUMMARY (
                    UUID text PRIMARY KEY,
                    Miner text,
                    Algo text,
                    START text,
                    END text,
                    TotalAcceptShares int,
                    TotalBadShares int,
                    Effeciency real,
                    AverageMinerHR text,
                    AveragePoolHR text,
                    SharesPerMin text,
                    AvgPower int,
                    Uptime text

                )
            '''
        )
        conn.commit()
        print("SUMMARY Table created successfully")
    except:
        print('SUMMARY Table Already Exists')

    try:
        conn.execute(
            '''
                CREATE TABLE STATS (
                    UUID text,
                    Time text PRIMARY KEY,
                    HashRateMiner text,
                    HashRatePool text,
                    ValidShares int,
                    BadShares int,
                    Power int
                )
            '''
        )
        conn.commit()
        print("STATS Table created successfully")
    except:
        print('STATS Table Already Exists')

def InsertNewSummary(UUID, Start):
    conn.execute("INSERT OR IGNORE INTO SUMMARY VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (UUID, Miner, Algo, Start, None, None, None, None, None, None, None, None, None))
    conn.commit()

def InsertEndSummary(UUID):
    secs = int(datetime.timestamp(datetime.now())) - int(UUID)
    td = TimeDelta(secs)
    mins = secs / 60
    conn.execute("UPDATE SUMMARY SET END = ? WHERE UUID = ?", 
        (datetime.now(), UUID))
    conn.commit()

def InsertAvgSummary(UUID, AcceptedShares, BadShares, MinerHashRate, Power, AveragePoolHashRate):
    secs = int(datetime.timestamp(datetime.now())) - int(UUID)
    td = TimeDelta(secs)
    mins = secs / 60
    conn.execute("UPDATE SUMMARY SET TotalAcceptShares = ?, TotalBadShares = ?, Effeciency = ?, AveragePoolHR = ?, SharesPerMin = ?, Uptime = ?, AvgPower = ?, AverageMinerHR = ? WHERE UUID = ?", 
        (AcceptedShares, BadShares, ((AcceptedShares + 1 - BadShares)*100)/(AcceptedShares+1), AveragePoolHashRate, AcceptedShares/mins, td, Power, MinerHashRate, UUID))
    conn.commit()

def InsertStats(UUID, Time, HRM, HRP, VS, BS, P):
    conn.execute("INSERT OR IGNORE INTO STATS VALUES (?, ?, ?, ?, ?, ?, ?)", (UUID, Time, HRM, HRP, VS, BS, P))
    conn.commit()

print(Miner, Algo, Port, Link)
CreateTables()

while(True):
    FindActive()
    while Miner is None:
        FindActive()
        print("No Miners are active, waiting 5 secs")
        time.sleep(5)
    print(Miner, Algo, Port, Link)
    if Miner == 'NBMiner':
        FirstResponse['stratum']['pool_hashrate_10m']= float(FirstResponse['stratum']['pool_hashrate_10m'].split(" ")[0]) * 1000000
        UUID = FirstResponse['start_time']
        InsertNewSummary(UUID, datetime.fromtimestamp(FirstResponse['start_time']))
        Active = True
        count = 1
        AveragePoolHashRate = float(FirstResponse['stratum']['pool_hashrate_10m'])
        AverageMinerHashRate = float(FirstResponse['miner']['total_hashrate_raw'])
        AveragePower = FirstResponse['miner']['total_power_consume']

        PAcceptedShares = FirstResponse['stratum']['accepted_shares']
        PBadShares = int(FirstResponse['stratum']['invalid_shares']) + int(FirstResponse['stratum']['rejected_shares'])
        PMinerHashRate = FirstResponse['miner']['total_hashrate_raw']
        PPoolHashRate = FirstResponse['stratum']['pool_hashrate_10m']
        PPower = FirstResponse['miner']['total_power_consume']

        while(Active):
            try:
                Response = requests.get(Link)
                JSON = Response.json()
                JSON['stratum']['pool_hashrate_10m']= float(JSON['stratum']['pool_hashrate_10m'].split(" ")[0]) * 1000000
                print("Miner is Alive, sleeping for 5 secs")

                MinerHashRate = JSON['miner']['total_hashrate_raw']
                AcceptedShares = JSON['stratum']['accepted_shares']
                BadShares = int(JSON['stratum']['invalid_shares']) + int(JSON['stratum']['rejected_shares'])
                PoolHashRate = JSON['stratum']['pool_hashrate_10m']
                Power = JSON['miner']['total_power_consume']
                
                InsertStats(
                    UUID, 
                    datetime.now(), 
                    MinerHashRate, 
                    PoolHashRate, 
                    AcceptedShares, 
                    BadShares, 
                    Power
                )

                PAcceptedShares = AcceptedShares
                PBadShares = BadShares
                PMinerHashRate = MinerHashRate
                PPoolHashRate = PoolHashRate
                PPower = Power

                AveragePoolHashRate = ((count * AveragePoolHashRate) + float(PoolHashRate)) / (count + 1)
                AveragePower = ((count * AveragePower) + float(Power)) / (count + 1)
                AverageMinerHashRate = ((count * AverageMinerHashRate) + float(MinerHashRate)) / (count + 1)
                count += 1

                InsertAvgSummary(UUID, PAcceptedShares, PBadShares, AverageMinerHashRate, AveragePower, AveragePoolHashRate)

                time.sleep(30)
            except:
                print("Miner Died")
                InsertEndSummary(UUID)
                Miner, Algo, Port, Link, FirstResponse = None, None, None, None, None
                Active = False
    elif Miner == 'T-Rex':
        UUID = FirstResponse['uuid']
        print('loki - ', UUID)
        InsertNewSummary(UUID, datetime.fromtimestamp(int(FirstResponse['uuid'])))
        Active = True
        count = 1
        AveragePoolHashRate = float(FirstResponse['hashrate_minute'])
        AverageMinerHashRate = float(FirstResponse['hashrate'])
        AveragePower = FirstResponse['gpus'][0]['power']
        PAcceptedShares = FirstResponse['accepted_count']
        PBadShares = int(FirstResponse['invalid_count']) + int(FirstResponse['rejected_count'])
        PMinerHashRate = FirstResponse['hashrate']
        PPoolHashRate = FirstResponse['hashrate_minute']
        PPower = FirstResponse['gpus'][0]['power']
        while(Active):
            try:
                Response = requests.get(Link)
                JSON = Response.json()
                uuid = str(int((int(datetime.timestamp(datetime.now())) - int(JSON['uptime']))/10))
                JSON['uuid'] = uuid + "5"
                print("Miner is Alive, sleeping for 5 secs", JSON['uuid'])

                AcceptedShares = JSON['accepted_count']
                BadShares = int(JSON['invalid_count']) + int(JSON['rejected_count'])
                MinerHashRate = JSON['hashrate']
                PoolHashRate = JSON['hashrate_minute']
                Power = JSON['gpus'][0]['power']

                InsertStats(
                    UUID, 
                    datetime.now(), 
                    MinerHashRate, 
                    PoolHashRate, 
                    AcceptedShares, 
                    BadShares, 
                    Power
                )

                PAcceptedShares = AcceptedShares
                PBadShares = BadShares
                PMinerHashRate = MinerHashRate
                PPoolHashRate = PoolHashRate
                PPower = Power

                AveragePoolHashRate = ((count * AveragePoolHashRate) + float(PoolHashRate)) / (count + 1)
                AveragePower = ((count * AveragePower) + float(Power)) / (count + 1)
                AverageMinerHashRate = ((count * AverageMinerHashRate) + float(MinerHashRate)) / (count + 1)
                count += 1

                InsertAvgSummary(UUID, PAcceptedShares, PBadShares, AverageMinerHashRate, AveragePower, AveragePoolHashRate)

                time.sleep(30)
            except:
                print("Miner Died")
                InsertEndSummary(UUID)
                Miner, Algo, Port, Link, FirstResponse = None, None, None, None, None
                Active = False

conn.close()

print(TimeDelta(int(input())))

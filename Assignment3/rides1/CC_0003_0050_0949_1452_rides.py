# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 09:31:03 2020

@author: 91948
"""


from flask import Flask, render_template,jsonify,request,abort
from datetime import datetime
import sys
import pymongo
import random
import json
import requests
import csv

myclient = pymongo.MongoClient("mongodb://172.31.35.178:27017/")
mydb = myclient["mydatabase"]
#userDB = mydb["users"]
rideDB = mydb["rides"]
#import mysql.connector

app = Flask(__name__)
hex_digits = set("0123456789abcdef")

places = []

file = csv.reader(open('AreaNameEnum.csv'), delimiter=',')
for line in file:
    if(line[0]!="Area No."):
        places.append(line[0])


origip = "3.88.128.139"
#ip = "172.31.82.178"
ipUser = "54.85.14.67" # Load Balancer IP
ipRide = "0.0.0.0" # The ride ip
portUser = "80" # Dont change 
portRide = "80" # Dont change
addrrUser = ipUser+':'+portUser
addrrRide = ipRide+':'+portRide
countFile = "countRide.json"



# for keeping track of number of calls
def incrementCount ():
    with open(countFile,'r+') as jsonFile:
        data = json.load(jsonFile)
        data["count"] = str(int(data["count"])+1)
        jsonFile.seek(0)
        json.dump(data,jsonFile)
        jsonFile.truncate()


# resets the count
def resetCount ():
    with open(countFile,'r+') as jsonFile:
        data = json.load(jsonFile)
        data["count"] = str(0)
        jsonFile.seek(0)
        json.dump(data,jsonFile)
        jsonFile.truncate()


# api count number of requests
'''
    gets the count
'''
@app.route("/api/v1/_count",methods = ["GET"])
def countRequest():
    with open(countFile,'r+') as jsonFile:
        data = json.load(jsonFile)
        count = int(data["count"])
    return json.dumps([count]),200

@app.route("/<path:text>", methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH','LINK','UNLINK','PURGE','LOCK','UNLOCK','PROPFIND','VIEW','COPY'])
def ALLcount(text):
    incrementCount()
    return text,405


# api to reset the count
@app.route("/api/v1/_count",methods = ["DELETE"])
def countRequestReset():
    resetCount()
    return jsonify(),200





# 2.3 Clear DB  RIDES
@app.route("/api/v1/db/clear",methods = ["POST"])
def clearRideDB ():
    if request.remote_addr != addrrUser and request.remote_addr != addrrRide:
        incrementCount()
    data = {
            "method" : "delete",
           "table" : "rideDB",
           "data" : {}
            }
    ret = requests.post("http://"+addrrRide+"/api/v1/db/write",json = data)

    if ret.status_code == 204:
        return jsonify({"Error":"Bad request. No data present."}),400
    elif ret.status_code == 400:
        return jsonify({"Error":"Bad request"}),400
    elif ret.status_code == 200:
        return jsonify(),200
        


    

# 3 Create New Ride
@app.route("/api/v1/rides",methods = ["POST"])
def makeRide():
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    data = request.get_json()
    username = data["created_by"]
    timestamp = data["timestamp"]
    source = str(data["source"])
    destination = str(data["destination"])

    findS = 0
    findD = 0
    print(places)
    if source in places:
        findS = 1
    else:
        return jsonify({"Error":"Bad Request (source doesnt exist)"}),400
    if destination in places:
        findD = 1
    else:
        return jsonify({"Error":"Bad Request (destination doesnt exist)"}),400
    if(source!=destination):
        ret = requests.get("http://"+addrrUser+"/api/v1/users",header={"Origin":origip})
        if username not in ret.json() :
            return jsonify({"Error":"Bad request. No User Present"}),400
        elif ret.status_code == 400:
            return jsonify({"Error":"Bad request"}),400
        elif ret.status_code == 200 and findS==1 and findD==1 and source!=destination:
            ## create ride
            data_part2 = {
                    "created_by" : username,
                    "timestamp" : timestamp,
                    "source" : source,
                    "destination" : destination,
                    "rideId" : str(random.getrandbits(256)),
                    "users":[username]
                    }
            write_query = {"method" : "write",
                           "table" : "rideDB",
                           "data" : data_part2
                          }

            ret = requests.post("http://"+addrrRide+"/api/v1/db/write", json = write_query)
            if ret.status_code == 200:
                return jsonify({}),201
            else:
                return jsonify({"Error":"Bad Request"}),str(ret.status_code)
        else:
            return jsonify({"Error":"Bad request"}),400
    else:
        return jsonify({"Error":"Bad request"}),400


#api 4
'''
input = /api/v1/rides?source=C&destination=A
'''
@app.route("/api/v1/rides",methods=["GET"])
def findRides():
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    src = str(request.args.get("source"))
    dist = str(request.args.get("destination"))
    findS = 0
    findD = 0
    #print(src,dist)
    if src in places:
        findS = 1
    else:
        return jsonify({"Error":"Bad Request (source doesnt exist)"}),400
    if dist in places:
        findD = 1
    else:
        return jsonify({"Error":"Bad Request (destination doesnt exist)"}),400
    if(findS==1 and findD==1 and src!=dist):
        data = {
                "table" : "rideDB",
                "columns" : ["rideId","created_by","timestamp"],
                "where" : ["source="+src,"destination="+dist]
                }

        ret = requests.post("http://"+addrrRide+"/api/v1/db/read",json = data)
        print(ret.text)
        if ret.status_code == 200:
            return json.loads(ret.text),200
        elif ret.status_code == 400:
            return jsonify({"Error":"Bad request"}),400
        elif ret.status_code == 204:
            print("no data present")
            return jsonify({}),204
    else:
        return jsonify({"Error":"Bad request"}),400


#api 5
'''
/api/v1/rides/123
'''
@app.route("/api/v1/rides/<rideId>",methods = ["GET"])
def findRideDetails (rideId):
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    query = {
                    "table" : "rideDB",
                    "columns" : ["rideId","source","destination","timestamp","created_by","users"],
                    "where" : ["rideId="+rideId]
                }

    ret = requests.post("http://"+addrrRide+"/api/v1/db/read", json = query)
    if ret.status_code == 200:

        return json.loads(ret.text),200
    elif ret.status_code == 400:
        return jsonify({"Error":"Bad request"}),400
    elif ret.status_code == 204:
        return jsonify({}),204

# api 6
'''
/api/v1/rides/<rideId>
{
    "username" : "bro"
}
'''
@app.route("/api/v1/rides/<rideId>",methods = ["POST"])
def joinRide(rideId):
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    data = request.get_json()
    username = data["username"]

    data = {
            "table" : "rideDB",
            "columns" : ["rideId","users"],
            "where" : ["rideId="+str(rideId)]
            }
    ret = requests.post("http://"+addrrRide+"/api/v1/db/read",json = data)
    if ret.status_code == 204:
        return jsonify({"Error":"Bad request(no data present)"}),400
    elif ret.status_code == 400:
        return jsonify({"Error":"Bad request (you have given wrong data)"}),400
    elif ret.status_code == 200:
        data = {
                "table" : "userDB",
                "columns" : ["username"],
                "where" : ["username="+str(username)]
                }
        #ret1 = requests.post("http://"+addrrUser+"/api/v1/db/read",json = data) # PUblic IP
        ret1 = requests.get("http://"+addrrUser+"/api/v1/users",header={"Origin":origip})
        if len(ret1.json())==0 :
            return jsonify({"error":"bad request(no data present)"}),400
        elif username not in ret1.json():
            return jsonify({"error":"bad request (you have given wrong data)"}),400
        elif ret1.status_code == 200:
            #### update here #######
            ret_json = json.loads(ret.text)
            list_of_users = list(ret_json["0"]["users"])
            if(str(username) not in list_of_users):
                list_of_users.append(str(username))
                query = {
                        "rideId" : str(rideId)
                        }
                up_query = {
                        "$set" : {
                                    "users" : list_of_users
                                }
                        }
                data_part3 = {
                        "method" : "update",
                        "table" : "rideDB",
                        "query" : query,
                        "insert" : up_query
                        }
                ret3 = requests.post("http://"+addrrRide+"/api/v1/db/write",json = data_part3)
                if (ret3.status_code == 200):
                    #update on knowing
                    return jsonify({}),200
                else:
                    return jsonify({"Error: Bad Request"}),400
            else:
                return jsonify({"error":"bad request (user already exists)"}),400
            #rideDB.update_one(query,up_query)

# api 7
'''
/api/v1/rides/12334546484
'''
@app.route("/api/v1/rides/<rideId>",methods = ["DELETE"])
def DeleteRides(rideId):
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    data = {
            "table" : "rideDB",
            "columns" : ["rideId"],
            "where" : ["rideId="+str(rideId)]
            }
    ret = requests.post("http://"+addrrRide+"/api/v1/db/read",json = data)

    if ret.status_code == 204:
        return jsonify({"error":"bad request(no data present)"}),400
    elif ret.status_code == 400:
        return jsonify({"error":"bad request (you have given wrong data)"}),400
    elif ret.status_code == 200:

        ## put delete here
        #######################################################################
        del_query = {
                    "rideId" : str(rideId)
                }
        data_part2 = {
                "method" : "delete",
                "table" : "rideDB",
                "data" : {"rideId" : str(rideId)}
                }
        ret2 = requests.post("http://"+addrrRide+"/api/v1/db/write",json = data_part2)
        if ret2.status_code == 200:
            return jsonify({"found" : "data"}),200
        else:
            return jsonify({"error":"bad request"}),400



#helper Api
# 2.1 List all Rides
@app.route("/api/v1/rides/all",methods = ["GET"])
def listAllRides():
    print("Users IP:",request.remote_addr)
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    data = {
       "table" : "rideDB",
       "columns" : ["rideId","source","destination","timestamp","created_by","users"],
       "where" : []
           }
    print("FInd alllll")
    ret = requests.post("http://"+addrrRide+"/api/v1/db/read",json = data)
    if ret.status_code == 204:
        return jsonify({"Error":"Bad request. No data present."}),204
    elif ret.status_code == 400:
        return jsonify({"Error":"Bad request"}),405
    elif ret.status_code == 200:
        return json.loads(ret.text),200
    else:
        return jsonify(),400;

# api9
'''
input {
       "table" : "table name",
       "columns" : ["col1","col2"],
       "where" : ["col=val","col=val"]
}
'''
@app.route("/api/v1/db/read",methods=["POST"])
def ReadFromDB():
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    data = request.get_json()
    print("Data got",data)
    collection = data["table"]
    columns = data["columns"]
    where = data["where"]
    query = dict()
    for q in where:
        query[q.split('=')[0]] = q.split('=')[1]
    query_result = None
    if collection == "userDB":
        query_result = userDB.find(query)
    elif collection == "rideDB":
        query_result = rideDB.find(query)
    else:
        print("Wrong table");
        return jsonify({}),400
    ### check if NULL is returnned
    #print(query_result[0])
    
    ## Testting the output ##
    if False:
        for i in userDB.find({}): print(i)
    try:
        print("Check",query_result[0])
    except IndexError:
        print("No data")
        return jsonify({}),204
    try:
        num = 0
        res_final = dict()
        for ret in query_result:
            result = dict()
            for key in columns:
                ##################### FIX this by perging the data base ##################
                try:
                    result[key] = ret[key]
                except:
                    pass
            res_final[num] = result
            num += 1
    except KeyError:
        print("While slicing bad Keys")
        return jsonify({}),400
    json.dumps(res_final)
    #print(json.dumps(res_final))
    return json.dumps(res_final),200





# api 8
'''
input {
       "method" : "write"
       "table" : "table :name",
       "data" : {"col1":"val1","col2":"val2"}
}
{
       "method" : "delete"
       "table" : "table :name",
       "data" : {"col1":"val1","col2":"val2"}
}
{
       "method" : "update"
       "table" : "table :name",
       "query" : {"col1":"val1","col2":"val2"},
       "insert" : {"$set" :
                   {
                           "b" : "c"
                   }
           }
}
'''
@app.route("/api/v1/db/write",methods=["POST"])
def WriteToDB():
    if request.remote_addr != addrrUser or request.remote_addr != addrrRide:
        incrementCount()
    data = request.get_json()
    if (data["method"] == "write"):
        collection = data["table"]
        insert_data = data["data"]
        if collection == "userDB":
            userDB.insert_one(insert_data)
        elif collection == "rideDB":
            rideDB.insert_one(insert_data)
        else:
            return jsonify({}),400
        print(collection,insert_data)
        return jsonify(),200
    elif (data["method"] == "delete"):
        collection = data["table"]
        delete_data = data["data"]
        if collection == "userDB":
            userDB.delete_many(delete_data)
        elif collection == "rideDB":
            rideDB.delete_many(delete_data)
        else:
            return jsonify({}),400
        return jsonify(),200
    elif (data["method"] == "update"):
        collection = data["table"]
        if collection == "userDB":
            userDB.update_one(data["query"],data["insert"])
        elif collection == "rideDB":
            rideDB.update_one(data["query"],data["insert"])
        else:
            return jsonify({}),400
        return jsonify(),200
    else:
        return jsonify(),400


def getDate ():
    yyyy,mm,dd = str(str(datetime.now()).split(' ')[0]).split('-')
    h,m,s = str(datetime.now()).split(' ')[1].split(':')
    s = s.split(".")[0]
    return dd + "-" + mm + "-" + yyyy + ":" + s + "-" + m + "-" + h




if __name__ == '__main__':
    app.debug=True
    app.run(host = ipRide, port = portRide)

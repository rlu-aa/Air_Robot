#coding=utf8
import itchat, time, urllib, urllib2, json, thread, requests, arrow, os
from itchat.content import *

AQI = {
    "CN": {
        "pm2_5": [
            (500, 500),
            (400, 350),
            (300, 250),
            (200, 150),
            (150, 115),
            (100, 75),
            (50, 35),
            (0, 0),
        ],
        "pm10": [
            (500, 600),
            (400, 500),
            (300, 420),
            (200, 350),
            (150, 250),
            (100, 75),
            (50, 50),
            (0, 0),
        ],
    },
    "US": {
        "pm2_5": [
            (500, 500.4),
            (400, 350.4),
            (300, 250.4),
            (200, 150.4),
            (150, 65.4),
            (100, 40.4),
            (50, 15.4),
            (0, 0)
        ],
        "pm10": [
            (500, 604),
            (400, 504),
            (300, 424),
            (200, 354),
            (150, 254),
            (100, 154),
            (50, 54),
            (0, 0)
        ]
    }
}


def calc_aqi(country="CN", **kwargs):
    results = []
    for pollutant, concentration in kwargs.items():
        j = 0
        for i, t in enumerate(AQI[country][pollutant]):
            aqi, conc = t
            if concentration > conc:
                j = i
                print("found breakpoint: country={}, pollutant={}, concentration={}, idx={}, conc={}".format(
                    country, pollutant, concentration, aqi, conc))
                break
        if j == 0:
            results.append(500)
        else:
            aqi_lo, conc_lo = AQI[country][pollutant][j]
            aqi_hi, conc_hi = AQI[country][pollutant][j - 1]
            results.append(aqi_lo + (concentration-conc_lo)*(aqi_hi-aqi_lo)/(conc_hi-conc_lo))
    print(results)
    return int(max(results))

def get_detail():
    payload = {'id': os.getenv('AAAIR_LASEREGGID')}
    try:
    	resp = requests.post("http://123.56.74.245:8080/topdata/getTopDetail", data=payload)
	resp.raise_for_status()
    except Exception as e:
	print str(e)
	return None,None,None
    jdata = resp.json()
    print "got air detail."
    return jdata["pm2_5"], jdata["pm10"], jdata["recieveTime"]

def send_to_chatroom(pm2_5, pm10, receive_time, room_name='A8K'):
    print "prepare to send to chatroom" + room_name
    itchat.get_chatrooms(update=True)
    rooms = itchat.search_chatrooms(name=room_name)
    if pm2_5 is None:
	message = u"服务器数据错误"
    else:
	message = u"办公室空气质量:\n\t-AQI(CN): {}\n\t-AQI(US): {}\n\t-PM2.5: {}μg/m^3\n\t-PM10: {}μg/m^3\n\t-updated at: {}".format(calc_aqi(country="CN", pm2_5=pm2_5, pm10=pm10), calc_aqi(country="US", pm2_5=pm2_5, pm10=pm10), pm2_5, pm10, receive_time)
    if rooms:
        print("chatroom {} is found".format(room_name))
        print '------------'
	print rooms[0]['UserName']
        itchat.send(message, rooms[0]['UserName'])
        time.sleep(.5)
    elif room_name.startswith('@'):
	print "direct send message to room id"
	itchat.send(message, room_name)
    else:
        print("{} is NOT found".format(room_name))

def tuling_auto_reply(uid, msg):
        if True:
            url = "http://www.tuling123.com/openapi/api"
            user_id = uid.replace('@', '')[:30]
            body = {'key': os.getenv('AAAIR_TULINGID'), 'info': msg.encode('utf8'), 'userid': user_id}
	    try:
	    	resp = requests.post(url, data=body)
		resp.raise_for_status()
	    except Exception as e:
		print str(e)
	    respond = resp.json()
            result = ''
            if respond['code'] == 100000:
                result = respond['text'].replace('<br>', '  ')
                result = result.replace(u'\xa0', u' ')
            elif respond['code'] == 200000:
                result = respond['url']
            elif respond['code'] == 302000:
                for k in respond['list']:
                    result = result + u"【" + k['source'] + u"】 " +\
                        k['article'] + "\t" + k['detailurl'] + "\n"
            else:
                result = respond['text'].replace('<br>', '  ')
                result = result.replace(u'\xa0', u' ')

            print '    ROBOT:', result
            return result
        else:
            return u"知道啦"

@itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING])
def text_reply(msg):
    print '	USER:'+msg['Content']
    reply = tuling_auto_reply(msg['FromUserName'], msg['Content'])
    print reply
    itchat.send(reply, msg['FromUserName'])

@itchat.msg_register(TEXT, isGroupChat=True)
def groupchat_reply(msg):
    head = msg['Content'].split()
    print head
    temp = msg['Content'].replace(head[0], '')[:30]
    print msg
    print len(head)
    if msg['isAt']:
        if len(head)<2:
	    detail_data = get_detail()
	    send_to_chatroom(detail_data[0],detail_data[1],detail_data[2],msg['FromUserName'])
        else:
            print 'in robot'
            reply = tuling_auto_reply(msg['FromUserName'], temp)
            print reply
            itchat.send(reply, msg['FromUserName'])

itchat.auto_login(hotReload=True, enableCmdQR=2)
#itchat.auto_login(hotReload=True)
thread.start_new_thread(itchat.run, ())
reportcount = 0
while(1):
    reportcount +=1
    if arrow.now('PRC').weekday()>4:
	if reportcount>6:
	    reportcount = 0
    elif arrow.now('PRC').hour<7:
	if reportcount>4:
	    reportcount = 0
    else:
	reportcount = 0
    if reportcount==0:
        detail_data = get_detail()
        send_to_chatroom(detail_data[0],detail_data[1],detail_data[2],"AAHQL")
    time.sleep(1800)

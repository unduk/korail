#!/usr/bin/python
#-*- coding: utf-8 -*-

import httplib, urllib, re
import sys, time, datetime
#from datetime import datetime
from dateutil.relativedelta import relativedelta
import smtplib
from email.mime.text import MIMEText
import lxml.html
#NTP LIB
import ntplib
from time import ctime
import socket, errno

# TODO 1.창측 좌석 필터링, 2: 말일에 걸칠 때 한 달 안 남았을 때

class Reservation:

	# Input list begins
	train = "KTX" # "KTX" | "새마을" | "무궁화"
	#psgCnt = "4"
	adult = "1"
	child = "0"

	resDate = "20160205"
	#depStation = u"서울"
	#arvStation = u"동대구"
	depStation = u"서울"
	arvStation = u"동대구"
	#timeRange = ["213000","220000"]
	timeRange = ["191000","191000"]
	#timeRange = ["220000","230000"]
	discount = "N"
	cardPw = "1409"
	# 파격가 할인
	isBigDiscount = "N"
	#trainNo = "00164" # 171: 1900, 357: 1903, 415: 1910, 340: 2125, 204: 0608
	trainNo = "00103" # 162: 1550, 171: 1900, 357: 1903, 415: 1910, 340: 2125, 204: 0608
	triggerTime = "070000"
	#triggerTime = "234100"
	#triggerTime = None
	# Input list ends

	isSeatFixed = False
	sendMailFlag = True
	period = 1
	cookieSet = {}
	cookie = ""
	#port = 8088
	
	httpConn = -1
	httpsConn = -1
	timeSkew = 0

	
		
	def __init__(self) :
	
		if len( sys.argv ) is not 1 :
			#출력을 파일로
			sys.stdout = open( "./logs/" + sys.argv[1], 'w')
			
			if sys.argv[2] == "1" :
				self.isBigDiscount = "N"
				self.depStation = u"서울"
				self.arvStation = u"동대구"
				self.resDate = sys.argv[3].replace( '-', '' )
				self.timeRange = [sys.argv[4].replace( ':', '' )+"00", sys.argv[5].replace( ':', '' )+"00" ]
				self.adult = sys.argv[6]
			elif sys.argv[2] == "2" :
				self.isBigDiscount = "N"
				self.depStation = u"동대구"
				self.arvStation = u"서울"
				self.resDate = sys.argv[3].replace( '-', '' )
				self.timeRange = [sys.argv[4].replace( ':', '' )+"00", sys.argv[5].replace( ':', '' )+"00" ]
				self.adult = sys.argv[6]
			elif sys.argv[2] == "3" :
				self.isBigDiscount = "Y"
				self.depStation = u"인천공항"
				self.arvStation = u"동대구"
				self.resDate = sys.argv[3].replace( '-', '' )
				self.trainNo = "00169"
			elif sys.argv[2] == "4" :
				self.isBigDiscount = "Y"
				self.depStation = u"서울"
				self.arvStation = u"동대구"
				self.resDate = sys.argv[3].replace( '-', '' )
				self.trainNo = "00161"
			elif sys.argv[2] == "5" :
				self.isBigDiscount = "Y"
				self.depStation = u"동대구"
				self.arvStation = u"서울"
				self.resDate = sys.argv[3].replace( '-', '' )
				self.trainNo = "00162"
			elif sys.argv[2] == "6" :
				self.isBigDiscount = "Y"
				self.depStation = u"동대구"
				self.arvStation = u"서울"
				self.resDate = sys.argv[3].replace( '-', '' )
				self.trainNo = "00418"

				
			
		#self.UserId = ""
		#self.UserPwd = ""
		self.UserId = ""
		self.UserPwd = ""
		self.stationMap = {u"서울": "0001", u"동대구": "0015", u"청도": "0016", u"부산": "0020", u"경산": "0024", u"용산": "0104", u"안양": "0135", u"광명": "0501", u"천안아산": "0502", u"인천공항": "0921", u"포항": "0515"  }

		self.psgCnt = str( int( self.adult ) + int( self.child ) )
		self.txtGoAbrdDt = self.resDate
		self.txtGoHour = self.timeRange[0]
		self.txtGoStart = self.depStation
		self.txtGoEnd = self.arvStation
		self.txtGoYoil = u"일"
		
		if not self.depStation in self.stationMap.keys() :
			print "Nonexistent departure station: %s"%self.depStation
			sys.exit(1)
		if not self.arvStation in self.stationMap.keys() :
			print "Nonexistent arrival station: %s"%self.arvStation
			sys.exit(1)		
			
		self.txtDptRsStn = self.stationMap[ self.depStation ]
		self.txtArvRsStn = self.stationMap[ self.arvStation ]
		
		if self.timeRange[0] > self.timeRange[1] :
			print "Invalid time range!"
			sys.exit(1)

		self.txtSeatAttCd_3 = "012" # 차실/좌석 : 창/내측/1인좌석종별, 000:기본, 011:1인석, 012:창측, 013:내측
		self.txtSeatAttCd_2 = "009" # 차실/좌석 : 좌석 방향, 000:기본, 009:순방향, 010:역방향
		self.txtSeatAttCd_4 = "015" # 차실/좌석 : 할인좌석종별, 015:기본, 019:유아동반
			
		if self.train == "KTX" :
			self.selGoTrain = "00"
			self.selGoTrainRa = "00" # KTX: 00, 새마을/ITX새마을: 08, ITX청춘: 09, 무궁화: 02, 공항직통: 06
			self.txtTrnClsfCd1 = "07" ## KTX: 00 KTX산천: 07
		elif self.train == "새마을" :
			self.selGoTrain = "08"
			self.selGoTrainRa = "08"
			self.txtTrnClsfCd1 = "08"
		elif self.train == "무궁화" :
			self.selGoTrain = "02"
			self.selGoTrainRa = "02"
			self.txtTrnClsfCd1 = "02"
		else :
			print "Unknown Train Class!"
			sys.exit(1)
			
		#self.cookieSet[ "WMONID" ] = "Rl-po7oYAsT"
		#self.cookie = "WMONID=Rl-po7oYAsT"

		if self.isBigDiscount == "Y" :
			while 1 :
				print "Calculating time skew..."
				if self.calculateTimeSkew() :
					print "Succeeded! Time skew: %d"%( self.timeSkew )
					break
				print "Failed... retrying after 1sec"
				time.sleep( 1 )
	
	def changeCookie(self, res_header) :

		cookies = re.findall( "Set-Cookie: (\w+)=(\w+?);", res_header )
		if len(cookies) == 0 :
			return False
			
		for key, value in cookies:
			self.cookieSet[ key ] = value

		self.cookie = ""			
		for key in self.cookieSet:
			if len(self.cookie) != 0:
				self.cookie += ';'
			self.cookie += key + '=' + self.cookieSet[key]
			
		print "Changing Cookie: %s"%self.cookie
		return True

	def login(self) :

		print "Trying Login ..."

		headers = {}
		headers[ 'Accept' ] = "image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/vnd.ms-excel, application/vnd.ms-powerpoint, application/msword, */*"
		headers[ 'Accept-Language' ] = "ko-KR"
		headers[ 'Referer' ] = "http://www.letskorail.com/korail/com/login.do"
		headers[ 'User-Agent' ] = "Mozilla/4.0 (compatible; MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET4.0C; .NET4.0E; moasigns=1.0.34; moasigns=1.0.34)"
		headers[ 'Content-Type' ] = "application/x-www-form-urlencoded"
		headers[ 'Host' ] = "www.letskorail.com"
		headers[ 'Connection' ] = "Keep-Alive"
		headers[ 'Cache-Control' ] = "no-cache"
		headers[ 'Cookie' ] = self.cookie

		message = {}
		message[ 'txtBookCnt' ] = ""
		message[ 'txtIvntDt' ] = ""
		message[ 'txtTotCnt' ] = ""
		message[ 'selValues' ] = ""
		message[ 'selInputFlg' ] = "2"
		message[ 'radIngrDvCd' ] = "2"
		message[ 'ret_url' ] = ""
		message[ 'hidMemberFlg' ] = "1"
		message[ 'txtHaeRang' ] = ""
		message[ 'hidEmailAdr' ] = ""
		message[ 'txtDv' ] = "2"
		message[ 'UserId' ] = self.UserId
		message[ 'UserPwd' ] = self.UserPwd
		message[ 'acsURI' ] = "http://www.letskorail.com:80/ebizsso/sso/acs"
		message[ 'providerName' ] = "Ebiz Sso"
		message[ 'forwardingURI' ] = "/ebizsso/sso/sp/service_proc.jsp"
		message[ 'loginForm' ] = "http://www.letskorail.com:80/ebizsso/sso/ip/login_form.jsp"
		message[ 'RelayState' ] = "/ebizsso/sso/sp/service_front.jsp"
		message[ 'IPType' ] = "Ebiz Sso Identity Provider"
		
		login_params = urllib.urlencode( message )
	
		conn = httplib.HTTPSConnection( "www.letskorail.com", timeout=5 )
		
		try:
			conn.request( "POST", "/korail/com/loginAction.do", login_params, headers )
			response = conn.getresponse()

			data = response.read()
			res_header = str(response.msg)
				
				
		#	print response.status, response.reason
		#	print response.msg
		#	print data	
				
			self.changeCookie( res_header )
		
			conn.close()
		except :
			conn.close()

		
	def logout(self) :

		print "Trying Logout ..."
				
		headers = {}
		headers[ 'Accept' ] = "*/*"
		headers[ 'X-Requested-With' ] = "XMLHttpRequest"
		headers[ 'Accept-Language' ] = "ko"
		headers[ 'Referer' ] = "http://www.letskorail.com/"
		headers[ 'User-Agent' ] = "Mozilla/4.0 (compatible; MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET4.0C; .NET4.0E; moasigns=1.0.34; moasigns=1.0.34)"
		headers[ 'Content-Type' ] = "application/x-www-form-urlencoded"
		headers[ 'Host' ] = "www.letskorail.com"
		headers[ 'Connection' ] = "Keep-Alive"
		headers[ 'Cache-Control' ] = "no-cache"
		headers[ 'Cookie' ] = self.cookie
		
		#conn = httplib.HTTPConnection( "www.letskorail.com", self.port, timeout=5 )
		conn = httplib.HTTPConnection( "www.letskorail.com", timeout=5 )

		try:
			conn.request( "POST", "/file/CACHE/prdMain.cache", "", headers )
			response = conn.getresponse()
			data = response.read()
			res_header = str(response.msg)

		#	print response.status, response.reason
		#	print response.msg
		#	print data

			conn.close()
		except:
			conn.close()
			return
		
		
		headers = {}
		headers[ 'Accept' ] = "application/json, text/javascript, */*; q=0.01"
		headers[ 'X-Requested-With' ] = "XMLHttpRequest"
		headers[ 'Accept-Language' ] = "ko"
		headers[ 'Referer' ] = "http://www.letskorail.com/"
		headers[ 'User-Agent' ] = "Mozilla/4.0 (compatible; MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET4.0C; .NET4.0E; moasigns=1.0.34; moasigns=1.0.34)"
		headers[ 'Content-Type' ] = "application/x-www-form-urlencoded"
		headers[ 'Host' ] = "www.letskorail.com"
		headers[ 'Connection' ] = "Keep-Alive"
		headers[ 'Cache-Control' ] = "no-cache"
		headers[ 'Cookie' ] = self.cookie
		
		#conn = httplib.HTTPConnection( "www.letskorail.com", self.port, timeout=5 )
		conn = httplib.HTTPConnection( "www.letskorail.com", timeout=5 )
		
		try:
			conn.request( "POST", "/file/CACHE/POP003.cache", "", headers )
			response = conn.getresponse()
			data = response.read()
			res_header = str(response.msg)

			conn.close()
		except:
			conn.close()
			return
		
		

	def getSchedule(self):

		sys.stdout.flush()
		
		print "\nRetrieving Schedules ... at %s"%( datetime.datetime.now() )
		headers = {}
		headers[ 'Accept' ] = "image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/vnd.ms-excel, application/vnd.ms-powerpoint, application/msword, */*"
		headers[ 'Referer' ] = "http://www.letskorail.com/ebizprd/EbizPrdTicketpr21100W_pr21110.do"
		headers[ 'Accept-Language' ] = "ko-KR"
		headers[ 'User-Agent' ] = "Mozilla/4.0 (compatible; MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET4.0C; .NET4.0E; moasigns=1.0.34; moasigns=1.0.34)"
		headers[ 'Content-Type' ] = "application/x-www-form-urlencoded"
		headers[ 'Host' ] = "www.letskorail.com"
		headers[ 'Cookie' ] = self.cookie
		headers[ 'Connection' ] = "Keep-Alive"
		headers[ 'Cache-Control' ] = "no-cache"

	#	headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/html, application/xhtml+xml, */*", "User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/5.0)", "Accept-Encoding": "deflate", "Connection": "Keep-Alive", "Cache-Control": "no-cache"}
	#	message = { 'ret_url':'', 'txtHaeRang':'', 'selInputFlg':'2', 'UserId':'', 'UserPwd':'', 'hidMemberFlg':'1', 'hidEmailAdr':'', 'txtDv':'1', 'Org':'1' }

		message = {}
		
		# 선택사항
		message[ 'txtPsgFlg_1' ] = self.psgCnt # 어른 숫자
		message[ 'txtPsgFlg_2' ] = "0" # 어린이 숫자
		message[ 'txtPsgFlg_3' ] = "0" # 65세이상 경로
		message[ 'txtPsgFlg_4' ] = "0" # 장애 1-3 급
		message[ 'txtPsgFlg_5' ] = "0" # 장애 4-6 급
		message[ 'selGoTrain' ] = self.selGoTrain
		message[ 'selGoTrainRa' ] = self.selGoTrainRa
		message[ 'txtSeatAttCd_3' ] = self.txtSeatAttCd_3
		message[ 'txtSeatAttCd_2' ] = self.txtSeatAttCd_2
		message[ 'txtSeatAttCd_4' ] = self.txtSeatAttCd_4
		message[ 'radJobId' ] = "1" # 1:직통, 2:환승, 3:왕복
		message[ 'txtGoStart' ] = self.txtGoStart
		message[ 'txtGoEnd' ] = self.txtGoEnd
		message[ 'selGoYear' ] = "2014"	
		message[ 'selGoMonth' ] = "09"
		message[ 'selGoDay' ] = "10"	
		message[ 'selGoHour' ] = "19"
		message[ 'txtGoHour' ] = self.txtGoHour	
		message[ 'txtGoYoil' ] = self.txtGoYoil
		message[ 'txtGoStartCode' ] = ""	
		message[ 'txtGoEndCode' ] = ""	
		
		# 설정사항
		message[ 'run' ] = ""
		message[ 'hidDiscount' ] = ""
		message[ 'txtGoAbrdDt' ] = self.txtGoAbrdDt
		message[ 'hidEasyTalk' ] = ""
		message[ 'txtMenuId' ] = "11" # 메뉴 아이디 초기화
		#message[ 'target' ] = ""
		message[ 'selGoSeat1' ] = "015"
		message[ 'selGoSeat2' ] = ""
		message[ 'txtPsgCnt1' ] = self.psgCnt		
		message[ 'txtPsgCnt2' ] = "0"
		
		# 히든
		message[ 'txtGoPage' ] = "1"
		message[ 'selGoRoom' ] = ""	
		message[ 'useSeatFlg' ] = ""
		message[ 'useServiceFlg' ] = ""
		message[ 'checkStnNm' ] = "Y"
		message[ 'SeandYo' ] = "N"
		message[ 'txtGoStartCode2' ] = ""	
		message[ 'txtGoEndCode2' ] = ""
		message[ 'selGoStartDay' ] = ""	

		params = urllib.urlencode( message )

		#pattern = re.compile( "Cookie: JSESSIONID=(?P<cookie>\w+)" )

		#conn = httplib.HTTPConnection( "www.letskorail.com", self.port, timeout=5 )
		if self.httpConn is -1 :
			self.httpConn = httplib.HTTPConnection( "www.letskorail.com", timeout=5 )

		try : 
			self.httpConn.request( "POST", "/ebizprd/EbizPrdTicketPr21111_i1.do", params, headers )		
			response = self.httpConn.getresponse()
			data = response.read()
			res_header = str(response.msg)

			#print response.status, response.reason
			#print response.msg
		#	print data

			#conn.close()
		except :
			self.httpConn.close()
			self.httpConn = -1
			return None
			
		self.changeCookie( res_header )
		
		return data

	def searchSeats(self, data) :
		print "Searching Seats: %s->%s, %s > (%s,%s)" % (self.depStation, self.arvStation, self.txtGoAbrdDt, self.timeRange[0], self.timeRange[1])
	
		documentElement = lxml.html.fromstring( data )
		
		classMagicName = "tbl_h"
		
		if len( documentElement.find_class( classMagicName ) ) == 0 :
			print "No train is available: %s > (%s,%s)" % (self.txtGoAbrdDt, self.timeRange[0], self.timeRange[1])
			return -1
		
		tableElement = documentElement.find_class( classMagicName )[0]
		rows = tableElement.findall( "tr" )	
		
		for i in range( 0, len(rows) ) :

			elements = rows[ i ][1].cssselect( 'a[href]' )
			#print elements[0].get( 'href' )
			
			[(txtRunDt, txtDptDt, txtTrnNo, txtTrnGpCd)] = re.findall( "txtRunDt=(\d+)&txtDptDt=(\d+)&txtTrnNo=(\d+)&txtTrnGpCd=(\d+)", elements[0].get( 'href' ) )

			[(depHour, depMin)] = re.findall( "(\d+):(\d+)", rows[ i ][2].text_content() )
			depTime = depHour + depMin + "00"
			#print "depTime: %s, timerange: %s" % (depTime, self.timeRange[1])

			if depTime > self.timeRange[1] :
				print "Train %s(%s)'s departure time is out of range: (%s,%s)"%(txtTrnNo, depTime, self.timeRange[0], self.timeRange[1])
				break
			
			elements = rows[ i ][5].cssselect( 'img[src]' )
			if re.search( "icon_apm_yes\.gif", elements[0].get( 'src' ) ) :
			#if re.search( u"예약하기", tdTags[7] ) :
				print "Train %s(%s): Available" % (txtTrnNo,depTime)
				
				elements = rows[ i ][5].cssselect( 'a[href]' )
				index = re.findall( "javascript:infochk\(1,(\d+)\);", elements[0].get( 'href' ) )
			
				return int( index[0] )
			elif re.search( "btn_selloff\.gif", elements[0].get( 'src' ) ):
			#elif re.search( u"좌석매진", tdTags[7] ):
					#print "[%s]"%tdTags[7]
				print "Train %s(%s): No seat" % (txtTrnNo,depTime)
			else :
				print "Unknown response message: " + u"좌석부족?"
						
		return -1
	
	def reserve2(self, data, index) :
		print "Trying reservation..."
			
		headers = {}
		headers[ 'Accept' ] = "text/html, application/xhtml+xml, */*"
		headers[ 'Referer' ] = " http://www.letskorail.com:8088/ebizprd/EbizPrdTicketPr21111_i1.do"
		headers[ 'Accept-Language' ] = "ko-KR"
		headers[ 'User-Agent' ] = "Mozilla/5.0 (MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko"
		headers[ 'Content-Type' ] = "application/x-www-form-urlencoded"
		headers[ 'Host' ] = "www.letskorail.com:8088"
		headers[ 'Cookie' ] = self.cookie
		headers[ 'Connection' ] = "Keep-Alive"
		headers[ 'Cache-Control' ] = "no-cache"
		headers[ 'DNT' ] = "1"

		if self.isBigDiscount == "Y" :
			pass
		else :		
			magic = "train\[%d\] = new train_info\(([^)]+)\);" % (index)
			paramsString = re.findall( magic, data )
			trimedParamsString = re.sub(r"\s+", "", paramsString[0])
			items = trimedParamsString.split( ',' )

		# 기차정보 세팅
		trainInfo = {}
		
		if self.isBigDiscount == "Y" :
			pass
		else :
			trainInfo[ 'txtGoAbrdDt' ] = items[0].replace( "\"", "" )
			trainInfo[ 'txtGoStartCode' ] = items[1].replace( "\"", "" )
			trainInfo[ 'txtGoEndCode' ] = items[2].replace( "\"", "" )
			trainInfo[ 'selGoTrain' ] = items[3].replace( "\"", "" )
			trainInfo[ 'selGoRoom' ] = items[4].replace( "\"", "" )
			trainInfo[ 'txtGoHour' ] = items[5].replace( "\"", "" )
			trainInfo[ 'txtGoTrnNo' ] = items[6].replace( "\"", "" )
			trainInfo[ 'useSeatFlg' ] = items[7].replace( "\"", "" )
			trainInfo[ 'useServiceFlg' ] = items[8].replace( "\"", "" )
			trainInfo[ 'selGoSeat' ] = items[9].replace( "\"", "" )
			trainInfo[ 'selGoSeat1' ] = items[10].replace( "\"", "" )
			trainInfo[ 'selGoSeat2' ] = items[11].replace( "\"", "" )
			trainInfo[ 'txtPsgCnt1' ] = items[12].replace( "\"", "" )
			trainInfo[ 'txtPsgCnt2' ] = items[13].replace( "\"", "" )
			trainInfo[ 'selGoService' ] = items[14].replace( "\"", "" )
			trainInfo[ 'h_trn_seq' ] = items[15].replace( "\"", "" )
			trainInfo[ 'h_chg_trn_dv_cd' ] = items[16].replace( "\"", "" ) # 직통:1, 환승:2
			trainInfo[ 'h_chg_trn_seq' ] = items[17].replace( "\"", "" )
			trainInfo[ 'h_dpt_rs_stn_cd' ] = items[18].replace( "\"", "" )
			trainInfo[ 'h_arv_rs_stn_cd' ] = items[19].replace( "\"", "" )
			trainInfo[ 'h_trn_no' ] = items[20].replace( "\"", "" )
			trainInfo[ 'h_yms_apl_flg' ] = items[21].replace( "\"", "" )
			trainInfo[ 'h_trn_clsf_cd' ] = items[22].replace( "\"", "" )
			trainInfo[ 'h_trn_gp_cd' ] = items[23].replace( "\"", "" )
			trainInfo[ 'h_seat_att_cd' ] = items[24].replace( "\"", "" )
			trainInfo[ 'h_run_dt' ] = items[25].replace( "\"", "" )
			trainInfo[ 'h_dpt_dt' ] = items[26].replace( "\"", "" )
			trainInfo[ 'h_dpt_tm' ] = items[27].replace( "\"", "" )
			trainInfo[ 'h_arv_dt' ] = items[28].replace( "\"", "" )
			trainInfo[ 'h_arv_tm' ] = items[29].replace( "\"", "" )
			trainInfo[ 'h_dlay_hr' ] = items[30].replace( "\"", "" )
			trainInfo[ 'h_rsv_wait_ps_cnt' ] = items[31].replace( "\"", "" )
			trainInfo[ 'h_dtour_flg' ] = items[32].replace( "\"", "" )
			trainInfo[ 'h_car_tp_cd' ] = items[33].replace( "\"", "" )
			trainInfo[ 'h_trn_cps_cd1' ] = items[34].replace( "\"", "" )
			trainInfo[ 'h_trn_cps_cd2' ] = items[35].replace( "\"", "" )
			trainInfo[ 'h_trn_cps_cd3' ] = items[36].replace( "\"", "" )
			trainInfo[ 'h_trn_cps_cd4' ] = items[37].replace( "\"", "" )
			trainInfo[ 'h_trn_cps_cd5' ] = items[38].replace( "\"", "" )
			trainInfo[ 'h_no_ticket_dpt_rs_stn_cd' ] = items[39].replace( "\"", "" )
			trainInfo[ 'h_no_ticket_arv_rs_stn_cd' ] = items[40].replace( "\"", "" )
			trainInfo[ 'h_nonstop_msg' ] = items[41].replace( "\"", "" )
			trainInfo[ 'h_dpt_stn_cons_ordr' ] = items[42].replace( "\"", "" )
			trainInfo[ 'h_arv_stn_cons_ordr' ] = items[43].replace( "\"", "" )
			trainInfo[ 'h_dpt_stn_run_ordr' ] = items[44].replace( "\"", "" )
			trainInfo[ 'h_arv_stn_run_ordr' ] = items[45].replace( "\"", "" )

		
		message = {}
		
		# 페이지 상단 기본
		if self.isBigDiscount == "Y" :
			message[ 'run' ] = ""
			message[ 'selGoTrain' ] = "00"
			message[ 'hidJobDv' ] = ""
		else :
			message[ 'hidDiscount' ] = ""
			message[ 'selGoTrain' ] = self.selGoTrain

		# 설정 - 히든
		if self.isBigDiscount == "Y" :
			message[ 'txtMenuId' ] = "41"
			message[ 'txtGdNo' ] = "B131209001GY" # 스페셜 상품 번호
			message[ 'txtPsgTpCd4' ] = "3"
			message[ 'txtPsgTpCd6' ] = "1"
			message[ 'txtDiscKndCd6' ] = "P11"
			message[ 'txtCompaCnt8' ] = "0"
			message[ 'txtCompaCnt9' ] = "0"
			#form2			
			#생략

		else :
			message[ 'txtMenuId' ] = "11"
			message[ 'txtPsgTpCd4' ] = ""
			message[ 'txtPsgTpCd6' ] = ""
			message[ 'txtDiscKndCd6' ] = ""
			message[ 'txtCompaCnt8' ] = ""
			message[ 'txtCompaCnt9' ] = ""
			message[ 'txtGoStartCode2' ] = ""	
			message[ 'txtGoEndCode2' ] = ""
			
			#form2
			message[ 'hidEasyTalk' ] = ""
			message[ 'selGoYear' ] = "2015"
			message[ 'selGoMonth' ] = "08"
			message[ 'selGoDay' ] = "02"
			message[ 'selGoHour' ] = "00"
			
		message[ 'ret_url' ] = ""

		message[ 'selGoSeat1' ] = "015"
		message[ 'selGoSeat2' ] = "015"
		message[ 'txtPsgCnt1' ] = "0"
		message[ 'txtPsgCnt2' ] = "0"
		message[ 'txtGoPage' ] = "1"
		message[ 'txtGoAbrdDt' ] = ""
		message[ 'selGoRoom' ] = ""	
		message[ 'useSeatFlg' ] = ""
		message[ 'useServiceFlg' ] = ""
		message[ 'checkStnNm' ] = "Y"
		message[ 'SeandYo' ] = "" #  서울 용산역 조회 플래그
			
		message[ 'txtPnrNo' ] = ""
		message[ 'hidStlFlg' ] = ""
		message[ 'chkTrnSeq' ] = "" # 열차순번
		message[ 'chkChgTrn1' ] = "" # 선행선택여부
		message[ 'chkChgTrn2' ] = "" # 후행선택여부
		message[ 'chkBtnImgTrn1' ] = "" # 선행버튼이미지
		message[ 'chkBtnImgTrn2' ] = "" # 후행버튼이미지
		message[ 'chkInitFlg' ] = "Y" # 초기화체크
			
		message[ 'ra' ] = "1" # 할인카드사용여부
		message[ 'txtSeatAttCd1' ] = ""
		message[ 'txtSeatAttCd2' ] = "" # 순/역방향
		message[ 'txtSeatAttCd3' ] = "" # 창측/내측
		message[ 'txtSeatAttCd4' ] = "" # 요구속성
		message[ 'txtSeatAttCd4_1' ] = "" # 요구속성
		message[ 'txtSeatAttCd5' ] = "" # 노트/어린이단독
		message[ 'strChkCpn' ] = "N" # 쿠폰 사용여부 체크
		message[ 'txtTotPsgCnt' ] = ""
		message[ 'txtSrcarCnt' ] = "0"
		message[ 'txtSrcarCnt1' ] = "0"
		message[ 'txtSrcarNo1' ] = "" # SEATMAP 예약
		message[ 'txtSrcarNo2' ] = ""
		message[ 'txtSrcarNo3' ] = ""
		message[ 'txtSrcarNo4' ] = ""
		message[ 'txtSrcarNo5' ] = ""
		message[ 'txtSrcarNo6' ] = ""
		message[ 'txtSrcarNo7' ] = ""
		message[ 'txtSrcarNo8' ] = ""
		message[ 'txtSrcarNo9' ] = ""
		message[ 'txtSeatNo1' ] = ""
		message[ 'txtSeatNo2' ] = ""
		message[ 'txtSeatNo3' ] = ""
		message[ 'txtSeatNo4' ] = ""
		message[ 'txtSeatNo5' ] = ""
		message[ 'txtSeatNo6' ] = ""
		message[ 'txtSeatNo7' ] = ""
		message[ 'txtSeatNo8' ] = ""
		message[ 'txtSeatNo9' ] = ""
		message[ 'txtSrcarNo1_1' ] = ""
		message[ 'txtSrcarNo1_2' ] = ""
		message[ 'txtSrcarNo1_3' ] = ""
		message[ 'txtSrcarNo1_4' ] = ""
		message[ 'txtSrcarNo1_5' ] = ""
		message[ 'txtSrcarNo1_6' ] = ""
		message[ 'txtSrcarNo1_7' ] = ""
		message[ 'txtSrcarNo1_8' ] = ""
		message[ 'txtSrcarNo1_9' ] = ""
		message[ 'txtSeatNo1_1' ] = ""
		message[ 'txtSeatNo1_2' ] = ""
		message[ 'txtSeatNo1_3' ] = ""
		message[ 'txtSeatNo1_4' ] = ""
		message[ 'txtSeatNo1_5' ] = ""
		message[ 'txtSeatNo1_6' ] = ""
		message[ 'txtSeatNo1_7' ] = ""
		message[ 'txtSeatNo1_8' ] = ""
		message[ 'txtSeatNo1_9' ] = ""
		message[ 'txtDmdSeatAtt1' ] = ""
		message[ 'txtDmdSeatAtt2' ] = ""
		message[ 'txtDmdSeatAtt3' ] = ""
		message[ 'txtDmdSeatAtt4' ] = ""
		message[ 'txtDmdSeatAtt5' ] = ""
		message[ 'txtDmdSeatAtt6' ] = ""
		message[ 'txtDmdSeatAtt7' ] = ""
		message[ 'txtDmdSeatAtt8' ] = ""
		message[ 'txtDmdSeatAtt9' ] = ""
		message[ 'txtDmdSeatAtt1_1' ] = ""
		message[ 'txtDmdSeatAtt1_2' ] = ""
		message[ 'txtDmdSeatAtt1_3' ] = ""
		message[ 'txtDmdSeatAtt1_4' ] = ""
		message[ 'txtDmdSeatAtt1_5' ] = ""
		message[ 'txtDmdSeatAtt1_6' ] = ""
		message[ 'txtDmdSeatAtt1_7' ] = ""
		message[ 'txtDmdSeatAtt1_8' ] = ""
		message[ 'txtDmdSeatAtt1_9' ] = ""
		message[ 'hidRsvChgNo' ] = ""
		message[ 'hidRsvTpCd' ] = "03" # 단체예약(09), 일반예약(03) 구분
			
		message[ 'txtPsgTpCd1' ] = "1"
		message[ 'txtPsgTpCd2' ] = "3"
		message[ 'txtPsgTpCd3' ] = "1"
		#message[ 'txtPsgTpCd4' ] = ""
		message[ 'txtPsgTpCd5' ] = "1"
		#message[ 'txtPsgTpCd6' ] = ""
		message[ 'txtPsgTpCd7' ] = "1"
		message[ 'txtPsgTpCd8' ] = ""
		message[ 'txtPsgTpCd9' ] = ""
		message[ 'txtDiscKndCd1' ] = "000"
		message[ 'txtDiscKndCd2' ] = "000"
		message[ 'txtDiscKndCd3' ] = "111"
		message[ 'txtDiscKndCd4' ] = ""
		message[ 'txtDiscKndCd5' ] = "131"
		#message[ 'txtDiscKndCd6' ] = ""
		message[ 'txtDiscKndCd7' ] = "112"
		message[ 'txtDiscKndCd8' ] = ""
		message[ 'txtDiscKndCd9' ] = ""
		message[ 'txtCompaCnt1' ] = "0"
		message[ 'txtCompaCnt2' ] = "0"
		message[ 'txtCompaCnt3' ] = "0"
		message[ 'txtCompaCnt4' ] = "0"
		message[ 'txtCompaCnt5' ] = "0"
		message[ 'txtCompaCnt6' ] = "0"
		message[ 'txtCompaCnt7' ] = "0"
		#message[ 'txtCompaCnt8' ] = ""
		#message[ 'txtCompaCnt9' ] = ""
		message[ 'txtStndFlg' ] = "" # 입석/OB 여부
		message[ 'txtJobId' ] = ""
		message[ 'txtJrnyCnt' ] = "" # 여정수
		message[ 'txtDptStnConsOrdr1' ] = ""
		message[ 'txtArvStnConsOrdr1' ] = ""
		message[ 'txtDptStnRunOrdr1' ] = ""
		message[ 'txtArvStnRunOrdr1' ] = ""
		message[ 'txtDptStnConsOrdr2' ] = ""
		message[ 'txtArvStnConsOrdr2' ] = ""
		message[ 'txtDptStnRunOrdr2' ] = ""
		message[ 'txtArvStnRunOrdr2' ] = ""
		message[ 'txtPsrmClCd1' ] = "" #좌석 종류, 1-일반실, 2-특실, 3-입석, 4-자유석, 5-특실seatmap, 6-일반실seatmap
		message[ 'txtJrnySqno1' ] = ""
		message[ 'txtJrnyTpCd1' ] = ""
		message[ 'txtDptDt1' ] = ""
		message[ 'txtDptRsStnCd1' ] = ""
		message[ 'txtDptTm1' ] = ""
		message[ 'txtArvRsStnCd1' ] = ""
		message[ 'txtArvTm1' ] = ""
		message[ 'txtTrnNo1' ] = ""
		message[ 'txtRunDt1' ] = ""
		message[ 'txtTrnClsfCd1' ] = self.txtTrnClsfCd1
		message[ 'txtTrnGpCd1' ] = ""
		message[ 'txtChgFlg1' ] = ""
		message[ 'txtDoTrnFlg1' ] = ""
		message[ 'txtPsrmClCd2' ] = ""
		message[ 'txtJrnySqno2' ] = ""
		message[ 'txtJrnyTpCd2' ] = ""
		message[ 'txtDptDt2' ] = ""
		message[ 'txtDptRsStnCd2' ] = ""
		message[ 'txtDptTm2' ] = ""
		message[ 'txtArvRsStnCd2' ] = ""
		message[ 'txtArvTm2' ] = ""
		message[ 'txtTrnNo2' ] = ""
		message[ 'txtRunDt2' ] = ""
		message[ 'txtTrnClsfCd2' ] = ""
		message[ 'txtTrnGpCd2' ] = ""
		message[ 'txtChgFlg2' ] = ""
		message[ 'txtDoTrnFlg2' ] = ""
		message[ 'selGoStartDay' ] = ""

		message[ 'PageInx' ] = ""

		
		# 설정 - 메뉴
		if self.isBigDiscount == "Y" :
			message[ 'txtPsgFlg_6' ] = "0" # 청소년 숫자
			message[ 'hidCndFlgDiscNo1' ] = "B121410002GY"
			message[ 'hidCndnDcntKndCd1' ] = "14"
			message[ 'hidCndFlgDiscNo2' ] = "B131209001GY"
			message[ 'hidCndnDcntKndCd2' ] = "13"
			message[ 'menu' ] = "2"
			# infomenu1, infomenu2 아이템들 생략함
			
			message[ 'hidOneTicketFlg' ] = "N"
		else :
			pass
		
		message[ 'txtPsgFlg_1' ] = "2" # 어른 숫자
		message[ 'txtPsgFlg_2' ] = "2" # 어린이 숫자
		message[ 'txtPsgFlg_3' ] = "0" # 65세이상 경로
		message[ 'txtPsgFlg_4' ] = "0" # 장애 1-3 급
		message[ 'txtPsgFlg_5' ] = "0" # 장애 4-6 급
		message[ 'selGoTrainRa' ] = self.selGoTrainRa
		message[ 'txtSeatAttCd_3' ] = self.txtSeatAttCd_3
		message[ 'txtSeatAttCd_2' ] = self.txtSeatAttCd_2
		message[ 'txtSeatAttCd_4' ] = self.txtSeatAttCd_4
		message[ 'radJobId' ] = "1" # 1:직통, 2:환승, 3:왕복
		message[ 'txtGoStart' ] = self.txtGoStart
		message[ 'txtGoEnd' ] = self.txtGoEnd
		message[ 'selGoYear' ] = "2014"	
		message[ 'selGoMonth' ] = "09"
		message[ 'selGoDay' ] = "10"	
		message[ 'selGoHour' ] = "19"
#		message[ 'txtGoHour' ] = self.txtGoHour	
		message[ 'txtGoYoil' ] = self.txtGoYoil
		message[ 'txtGoStartCode' ] = ""	
		message[ 'txtGoEndCode' ] = ""	
		
		
		# 설정 - inqSchedule : 조회버튼 누른 후
		if self.isBigDiscount == "Y" :
			# message[ 'PageInx' ] = ""
			message[ 'txtMenuId' ] = "41"
		else :
			message[ 'txtMenuId' ] = "11" # 메뉴 아이디 초기화

		message[ 'txtGoAbrdDt' ] = self.txtGoAbrdDt
		message[ 'txtGoHour' ] = self.txtGoHour				
		message[ 'selGoSeat1' ] = "015"
		message[ 'selGoSeat2' ] = ""
		message[ 'txtPsgCnt1' ] = self.psgCnt		
		message[ 'txtPsgCnt2' ] = "0"
		message[ 'SeandYo' ] = "N" #  서울 용산역 조회 플래그
		#message[ 'target' ] = ""

		
		# 설정 - infocheck : 예약버튼 누른 후
		if self.isBigDiscount == "Y" : # BY function initSettingParam()
			message[ 'txtPsgTpCd1' ] = "1" 
			message[ 'txtPsgTpCd2' ] = "3"
			message[ 'txtPsgTpCd3' ] = "1"
			message[ 'txtPsgTpCd4' ] = "3"
			message[ 'txtPsgTpCd5' ] = "1"
			message[ 'txtPsgTpCd6' ] = "1"
			message[ 'txtPsgTpCd7' ] = "1"
			message[ 'txtPsgTpCd8' ] = ""
			message[ 'txtPsgTpCd9' ] = ""
			message[ 'txtDiscKndCd1' ] = "000"
			message[ 'txtDiscKndCd2' ] = "000"
			message[ 'txtDiscKndCd3' ] = "111"
			message[ 'txtDiscKndCd4' ] = ""
			message[ 'txtDiscKndCd5' ] = "131"
			message[ 'txtDiscKndCd6' ] = "P11"
			message[ 'txtDiscKndCd7' ] = "112"
			message[ 'txtDiscKndCd8' ] = ""
			message[ 'txtDiscKndCd9' ] = ""
		else :
			message[ 'txtPsgTpCd1' ] = "1"
			message[ 'txtPsgTpCd2' ] = "3"
			message[ 'txtPsgTpCd3' ] = "1"
			message[ 'txtPsgTpCd4' ] = ""
			message[ 'txtPsgTpCd5' ] = "1"
			message[ 'txtPsgTpCd6' ] = ""
			message[ 'txtPsgTpCd7' ] = "1"
			message[ 'txtPsgTpCd8' ] = "1"
			message[ 'txtPsgTpCd9' ] = "1"
			message[ 'txtDiscKndCd1' ] = "000"
			message[ 'txtDiscKndCd2' ] = "000"
			message[ 'txtDiscKndCd3' ] = "111"
			message[ 'txtDiscKndCd4' ] = ""
			message[ 'txtDiscKndCd5' ] = "131"
			message[ 'txtDiscKndCd6' ] = ""
			message[ 'txtDiscKndCd7' ] = "112"
			message[ 'txtDiscKndCd8' ] = ""
			message[ 'txtDiscKndCd9' ] = ""
			
			message[ 'txtSeatAttCd4' ] = trainInfo[ 'h_seat_att_cd' ]
			
			
		
		message[ 'txtGoAbrdDt' ] = self.txtGoAbrdDt
		message[ 'txtPsrmClCd1' ] = "1" #chkBtnRsvSelect() 좌석 종류, 1-일반실, 2-특실, 3-입석, 4-자유석, 5-특실seatmap, 6-일반실seatmap

		message[ 'txtJobId' ] = "1101" # "1101" ->  /* 개인예약, "1102" ->  /* 예약대기, "1103" ->  /* SEATMAP예약, "1105" -> one ticket
		
		if self.isBigDiscount == "Y" : 
			message[ 'txtJrnyCnt' ] = "1" # 여정수
		else :
			message[ 'txtJrnyCnt' ] = trainInfo[ 'h_chg_trn_dv_cd' ] # 여정수
			
		message[ 'txtCompaCnt1' ] = self.adult # 일반 어른 
		message[ 'txtCompaCnt2' ] = self.child # 일반 어린이
		message[ 'txtCompaCnt3' ] = "0" # 장애1-3 어른
		message[ 'txtCompaCnt4' ] = "0" # 장애1-3 어린이
		message[ 'txtCompaCnt5' ] = "0" # 경로 어른
		message[ 'txtCompaCnt6' ] = "0" # 청소년
		message[ 'txtCompaCnt7' ] = "0" # 장애4-6 어른
		message[ 'txtTotPsgCnt' ] = self.psgCnt	
		
		message[ 'txtSeatAttCd1' ] = "000"
		message[ 'txtSeatAttCd2' ] = "009" # 순/역방향
		message[ 'txtSeatAttCd3' ] = "012" # 창측/내측
		message[ 'txtSeatAttCd4' ] = "015" # 요구속성
		message[ 'txtSeatAttCd5' ] = "000" # 노트/어린이단독		
		
		message[ 'txtJrnyTpCd1' ] = "11" #편도
		
		message[ 'txtJrnySqno1' ] = "001"
		
		if self.isBigDiscount == "Y" : 
			message[ 'txtDptDt1' ] = self.txtGoAbrdDt
			message[ 'txtDptRsStnCd1' ] = self.txtDptRsStn
			message[ 'txtDptTm1' ] = "" # 수정이 필요할 수 있음
			message[ 'txtArvRsStnCd1' ] = self.txtArvRsStn
			message[ 'txtArvTm1' ] = "" # 수정이 필요할 수 있음
			message[ 'txtTrnNo1' ] = self.trainNo
			message[ 'txtRunDt1' ] = self.txtGoAbrdDt
			message[ 'txtTrnClsfCd1' ] = self.txtTrnClsfCd1
			message[ 'txtTrnGpCd1' ] = "100"
			
			message[ 'txtChgFlg1' ] = "N"
			message[ 'txtDptStnConsOrdr1' ] = "000007"
			message[ 'txtArvStnConsOrdr1' ] = ""
			message[ 'txtDptStnRunOrdr1' ] = "000001"
			message[ 'txtArvStnRunOrdr1' ] = ""
			message[ 'txtDoTrnFlg1' ] = ""

		else :
			message[ 'txtDptDt1' ] = trainInfo[ 'h_dpt_dt' ]
			message[ 'txtDptRsStnCd1' ] = trainInfo[ 'h_dpt_rs_stn_cd' ]
			message[ 'txtDptTm1' ] = trainInfo[ 'h_dpt_tm' ]
			message[ 'txtArvRsStnCd1' ] = trainInfo[ 'h_arv_rs_stn_cd' ]
			message[ 'txtArvTm1' ] = trainInfo[ 'h_arv_tm' ]
			message[ 'txtTrnNo1' ] = trainInfo[ 'h_trn_no' ]
			message[ 'txtRunDt1' ] = trainInfo[ 'h_run_dt' ]
			message[ 'txtTrnClsfCd1' ] = trainInfo[ 'h_trn_clsf_cd' ]
			message[ 'txtTrnGpCd1' ] = trainInfo[ 'h_trn_gp_cd' ]
			
			message[ 'txtChgFlg1' ] = "N"
			message[ 'txtDptStnConsOrdr1' ] = trainInfo[ 'h_dpt_stn_cons_ordr' ]
			message[ 'txtArvStnConsOrdr1' ] = trainInfo[ 'h_arv_stn_cons_ordr' ]
			message[ 'txtDptStnRunOrdr1' ] = trainInfo[ 'h_dpt_stn_run_ordr' ]
			message[ 'txtArvStnRunOrdr1' ] = trainInfo[ 'h_arv_stn_run_ordr' ]
	
		
			if trainInfo[ 'h_trn_cps_cd1' ] == "L" or trainInfo[ 'h_trn_cps_cd2' ] == "L" or trainInfo[ 'h_trn_cps_cd3' ] == "L" or trainInfo[ 'h_trn_cps_cd4' ] == "L" or trainInfo[ 'h_trn_cps_cd5' ] == "L" :
				message[ 'txtDoTrnFlg1' ] = "L"
		
		if self.isSeatFixed == True :
			message[ 'txtPsrmClCd1' ] = '1'
			if self.isBigDiscount == "Y" : 
				message[ 'txtMenuId' ] = '44'
			else :
				message[ 'txtMenuId' ] = '14'
			message[ 'txtPsgCnt1' ] = "0"
			message[ 'txtSrcarCnt' ] = "1"
			message[ 'txtSrcarNo1' ] = "0010" # SEATMAP 예약
			message[ 'txtSeatNo1' ] = "17" # 4A 좌석
			message[ 'txtDmdSeatAtt1' ] = "015"
			message[ 'txtJobId' ] = "1103"
		

		params = urllib.urlencode( message )
		
		#conn2 = httplib.HTTPConnection( "www.letskorail.com", self.port, timeout=5 )
		if self.httpConn is -1 :
			self.httpConn = httplib.HTTPConnection( "www.letskorail.com", timeout=5 )
		
		try : 
			self.httpConn.request( "POST", "/ebizprd/EbizPrdTicketPr12111_i1.do", params, headers )
			response = self.httpConn.getresponse()
			data = response.read()
			res_header = str(response.msg)
			#self.httpConn.close()
		except socket.error as e:
			print e
			self.httpConn.close()
			self.httpConn = -1
			return -1

		self.changeCookie( res_header )

			
		if response.status == 200 :
				print "Reservation Completed."
				# 테이블 class="tbl_h tbl_lin01", tbody id="infos" 에서 좌석정보를 추출할 수 있음
				#print data
				return 0

		elif response.status == 302 :
				print "Reservation Failed. Trying continues."
				
				conn3 = httplib.HTTPSConnection( "www.letskorail.com", timeout=5 )
				conn3.request( "POST", "/docs/pz/Error_pr_1.jsp", params, headers )
				response = conn3.getresponse()
				data = response.read()
				res_header = str(response.msg)
				conn3.close()
				
				documentElement = lxml.html.fromstring( data )
				classMagicName = "guide_msg"
		
				if len( documentElement.find_class( classMagicName ) ) == 0 :
					print "No guide message is available"
					return -1
			
				tableElement = documentElement.find_class( classMagicName )[0]
				print tableElement.text_content()

		
				self.changeCookie( res_header )
			
				return -1
		else :
				print "Reservation Failed: Unknown failure. Aborted."
				print response.status, response.reason
				print response.msg
				print unicode(data)
				return -1
		
	def reserve(self,txtRunDt, txtTrnNo) :
		print "Trying reservation: %s, %s ..." % (txtRunDt, txtTrnNo)
			
		headers = {}
		headers[ 'Accept' ] = "image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/vnd.ms-excel, application/vnd.ms-powerpoint, application/msword, */*"
		headers[ 'Referer' ] = "http://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do"
		headers[ 'Accept-Language' ] = "ko-KR"
		headers[ 'User-Agent' ] = "Mozilla/4.0 (compatible; MSIE 9.0;IPMS/665D4C6E-14FB401E6E6-00000002602A; Windows NT 6.1; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET4.0C; .NET4.0E; moasigns=1.0.34; moasigns=1.0.34)"
		headers[ 'Content-Type' ] = "application/x-www-form-urlencoded"
		headers[ 'Host' ] = "www.letskorail.com"
		headers[ 'Cookie' ] = self.cookie
		headers[ 'Connection' ] = "Keep-Alive"
		headers[ 'Cache-Control' ] = "no-cache"

		if self.isBigDiscount == "Y" :
			message = {}
			message[ 'hidDiscount' ] = ""
			message[ 'selGoTrain' ] = self.selGoTrain # 무궁화: 02
			message[ 'txtPsgFlg_1' ] = "1"
			message[ 'txtPsgFlg_2' ] = "0"
			message[ 'txtPsgFlg_3' ] = "0"
			message[ 'txtPsgFlg_4' ] = "0"			
			message[ 'txtPsgFlg_5' ] = "0"
			message[ 'txtPsgFlg_6' ] = "0"
			message[ 'txtSeatAttCd_3' ] = self.txtSeatAttCd_3 # 무궁화: 11
			message[ 'txtSeatAttCd_2' ] = self.txtSeatAttCd_2 # 무궁화: 00
			message[ 'txtSeatAttCd_4' ] = "15"
			message[ 'selGoTrainRa' ] = self.selGoTrainRa
			message[ 'menu' ] = "5"
			message[ 'radJoFlg' ] = "N"
			message[ 'radJobId' ] = "1"
			message[ 'txtGoStart' ] = self.txtGoStart
			message[ 'txtGoEnd' ] = self.txtGoEnd				
			message[ 'txtGoStartCode' ] = ""#self.txtDptRsStn	
			message[ 'txtGoEndCode' ] = ""#self.txtArvRsStn				
			message[ 'selGoYear' ] = "2014"	
			message[ 'selGoMonth' ] = "09"
			message[ 'selGoDay' ] = "20"	
			message[ 'selGoHour' ] = "00"			
			message[ 'txtGoHour' ] = ""	
			message[ 'txtGoYoil' ] = ""	
			message[ 'hidOneTicketFlg' ] = "N"	
			message[ 'txtPnrNo' ] = ""
			message[ 'hidStlFlg' ] = ""
			message[ 'txtGdNo' ] = "131209001"
			message[ 'ret_url' ] = ""
			message[ 'selGoSeat1' ] = "15"	
			message[ 'selGoSeat2' ] = "15"	
			message[ 'txtPsgCnt1' ] = "0"		
			message[ 'txtPsgCnt2' ] = "0"		
			message[ 'txtGoPage' ] = "1"		
			message[ 'txtGoAbrdDt' ] = txtRunDt		
			message[ 'selGoRoom' ] = ""		
			message[ 'useSeatFlg' ] = ""	
			message[ 'useServiceFlg' ] = ""	
			message[ 'checkStnNm' ] = "Y"	
			message[ 'txtMenuId' ] = "41"
			message[ 'SeandYo' ] = ""	
			message[ 'chkTrnSeq' ] = ""	
			message[ 'chkChgTrn1' ] = ""
			message[ 'chkChgTrn2' ] = ""
			message[ 'chkBtnImgTrn1' ] = ""
			message[ 'chkBtnImgTrn2' ] = ""
			message[ 'chkInitFlg' ] = "Y"
			message[ 'ra' ] = "1"
			message[ 'txtSeatAttCd1' ] = "00"
			message[ 'txtSeatAttCd2' ] = self.txtSeatAttCd_2
			message[ 'txtSeatAttCd3' ] = "12"
			message[ 'txtSeatAttCd4' ] = "15"
			message[ 'txtSeatAttCd5' ] = "00"
			message[ 'strChkCpn' ] = "N"	
			message[ 'txtTotPsgCnt' ] = "1"
			message[ 'txtSrcarCnt' ] = "0"
			message[ 'txtSrcarNo1' ] = ""
			message[ 'txtSrcarNo2' ] = ""
			message[ 'txtSrcarNo3' ] = ""
			message[ 'txtSrcarNo4' ] = ""
			message[ 'txtSrcarNo5' ] = ""
			message[ 'txtSrcarNo6' ] = ""
			message[ 'txtSrcarNo7' ] = ""
			message[ 'txtSrcarNo8' ] = ""
			message[ 'txtSrcarNo9' ] = ""
			message[ 'txtSeatNo1' ] = ""
			message[ 'txtSeatNo2' ] = ""
			message[ 'txtSeatNo3' ] = ""
			message[ 'txtSeatNo4' ] = ""
			message[ 'txtSeatNo5' ] = ""
			message[ 'txtSeatNo6' ] = ""
			message[ 'txtSeatNo7' ] = ""	
			message[ 'txtSeatNo8' ] = ""
			message[ 'txtSeatNo9' ] = ""
			message[ 'hidRsvChgNo' ] = ""
			message[ 'hidRsvTpCd' ] = "03"
			message[ 'txtPsgTpCd1' ] = "1"	
			message[ 'txtPsgTpCd2' ] = "3"
			message[ 'txtPsgTpCd3' ] = "1"
			message[ 'txtPsgTpCd4' ] = "3"
			message[ 'txtPsgTpCd5' ] = "1"
			message[ 'txtPsgTpCd6' ] = "1"	
			message[ 'txtPsgTpCd7' ] = "1"
			message[ 'txtPsgTpCd8' ] = ""	
			message[ 'txtPsgTpCd9' ] = ""
			message[ 'txtDiscKndCd1' ] = ""
			message[ 'txtDiscKndCd2' ] = ""
			message[ 'txtDiscKndCd3' ] = "P21"
			message[ 'txtDiscKndCd4' ] = "P21"		
			message[ 'txtDiscKndCd5' ] = "P41"
			message[ 'txtDiscKndCd6' ] = "P11"	
			message[ 'txtDiscKndCd7' ] = "P22"
			message[ 'txtDiscKndCd8' ] = ""
			message[ 'txtDiscKndCd9' ] = ""
			message[ 'txtCompaCnt1' ] = self.psgCnt
			message[ 'txtCompaCnt2' ] = "0"		
			message[ 'txtCompaCnt3' ] = "0"
			message[ 'txtCompaCnt4' ] = "0"	
			message[ 'txtCompaCnt5' ] = "0"
			message[ 'txtCompaCnt6' ] = "0"
			message[ 'txtCompaCnt7' ] = "0"
			message[ 'txtCompaCnt8' ] = ""
			message[ 'txtCompaCnt9' ] = ""		
			message[ 'txtStndFlg' ] = ""
			message[ 'txtJobId' ] = "1101"
			message[ 'txtJrnyCnt' ] = "1"		
			message[ 'txtPsrmClCd1' ] = "1"
			message[ 'txtJrnySqno1' ] = "001"	
			message[ 'txtJrnyTpCd1' ] = "11"
			message[ 'txtDptDt1' ] = txtRunDt
			message[ 'txtDptRsStnCd1' ] = self.txtDptRsStn
			message[ 'txtDptTm1' ] = "163000"
			message[ 'txtArvRsStnCd1' ] = self.txtArvRsStn		
			message[ 'txtArvTm1' ] = "182500"
			message[ 'txtTrnNo1' ] = txtTrnNo
			message[ 'txtRunDt1' ] = txtRunDt	
			message[ 'txtTrnClsfCd1' ] = self.txtTrnClsfCd1
			message[ 'txtChgFlg1' ] = "N"	
			message[ 'txtDoTrnFlg1' ] = "L"
			message[ 'txtPsrmClCd2' ] = ""
			message[ 'txtJrnySqno2' ] = ""
			message[ 'txtJrnyTpCd2' ] = ""
			message[ 'txtDptDt2' ] = ""	
			message[ 'txtDptRsStnCd2' ] = ""		
			message[ 'txtDptTm2' ] = ""
			message[ 'txtArvRsStnCd2' ] = ""	
			message[ 'txtArvTm2' ] = ""
			message[ 'txtTrnNo2' ] = ""
			message[ 'txtRunDt2' ] = ""
			message[ 'txtTrnClsfCd2' ] = ""
			message[ 'txtChgFlg2' ] = ""
			message[ 'txtDoTrnFlg2' ] = ""	
			message[ 'selGoStartDay' ] = ""
			message[ 'PageInx' ] = ""			
			
			
			#message[ 'txtGoStartCode2' ] = ""	
			#message[ 'txtGoEndCode2' ] = ""	
			#message[ 'txtMenuId' ] = "11" # menu 로 대체된 듯
			#message[ 'hidEasyTalk' ] = ""
			
		elif self.discount == "Y" :
			print "Trying Discount"
			message = {}
			
			message[ 'hidPsgTpCd1_1' ]="1,000"
			message[ 'hidPsgFlg1_1' ]="1"
			message[ 'hidCardCode_1' ]="C01"
			message[ 'hidCardNm_1' ]="7742579001"
			message[ 'hidCardPw_1' ] = self.cardPw
			message[ 'txtPsgTpCd1_1' ] = ""
			message[ 'txtPsgTpCd1_2' ] = ""
			message[ 'txtPsgTpCd1_3' ] = ""
			message[ 'txtPsgTpCd1_4' ] = ""
			message[ 'txtPsgTpCd1_5' ] = ""
			message[ 'txtPsgTpCd1_6' ] = ""
			message[ 'txtPsgTpCd1_7' ] = ""
			message[ 'txtPsgTpCd1_8' ] = ""
			message[ 'txtPsgTpCd1_9' ] = ""
			message[ 'txtPsgFlg1_1' ] = "1"
			message[ 'txtPsgFlg1_2' ] = ""
			message[ 'txtPsgFlg1_3' ] = ""
			message[ 'txtPsgFlg1_4' ] = ""
			message[ 'txtPsgFlg1_5' ] = ""
			message[ 'txtPsgFlg1_6' ] = ""
			message[ 'txtPsgFlg1_7' ] = ""
			message[ 'txtPsgFlg1_8' ] = ""
			message[ 'txtPsgFlg1_9' ] = ""
			message[ 'txtCardCode_1' ] = "C01"
			message[ 'txtCardCode_2' ] = ""
			message[ 'txtCardCode_3' ] = ""
			message[ 'txtCardCode_4' ] = ""
			message[ 'txtCardCode_5' ] = ""
			message[ 'txtCardCode_6' ] = ""
			message[ 'txtCardCode_7' ] = ""
			message[ 'txtCardCode_8' ] = ""
			message[ 'txtCardCode_9' ] = ""
			message[ 'txtCardNm_1' ] = "7742579001"
			message[ 'txtCardNm_2' ] = ""
			message[ 'txtCardNm_3' ] = ""
			message[ 'txtCardNm_4' ] = ""
			message[ 'txtCardNm_5' ] = ""
			message[ 'txtCardNm_6' ] = ""
			message[ 'txtCardNm_7' ] = ""
			message[ 'txtCardNm_8' ] = ""
			message[ 'txtCardNm_9' ] = ""
			message[ 'txtCardPw_1' ] = "1409"
			message[ 'txtCardPw_2' ] = ""
			message[ 'txtCardPw_3' ] = ""
			message[ 'txtCardPw_4' ] = ""
			message[ 'txtCardPw_5' ] = ""
			message[ 'txtCardPw_6' ] = ""
			message[ 'txtCardPw_7' ] = ""
			message[ 'txtCardPw_8' ] = ""
			message[ 'txtCardPw_9' ] = ""
			message[ 'strCompaCnt1' ] = "1"
			message[ 'strCompaCnt2' ] = "0"
			message[ 'strCompaCnt3' ] = "0"
			message[ 'strCompaCnt4' ] = "0"
			message[ 'strCompaCnt5' ] = "0"
			message[ 'strCompaCnt6' ] = "0"
			message[ 'strCompaCnt7' ] = "0"
			message[ 'h_dg_gubun' ] = "N"
			message[ 'StrPsFamily' ] = ""
			message[ 'h_free_disc_cert_no' ] = ""
			message[ 'StrPsTot' ] = "0"
			message[ 'stf_fmly_sqno' ] = ""
			message[ 'ra' ] = "2"
			message[ 'hidDiscount' ] = ""
			message[ 'selGoTrain' ] = self.selGoTrain # 무궁화: 02
			message[ 'txtPsgFlg_1' ] = "1"
			message[ 'txtPsgFlg_2' ] = "0"
			message[ 'txtPsgFlg_3' ] = "0"
			message[ 'txtPsgFlg_4' ] = "0"
			message[ 'txtPsgFlg_5' ] = "0"
			message[ 'chkCpn' ] = "Y"
			message[ 'txtSeatAttCd_3' ] = self.txtSeatAttCd_3 # 무궁화: 11
			message[ 'txtSeatAttCd_2' ] = self.txtSeatAttCd_2 # 무궁화: 00
			message[ 'txtSeatAttCd_4' ] = "15"
			message[ 'selGoTrainRa' ] = self.selGoTrainRa
			message[ 'radJobId' ] = "1"
			message[ 'txtGoStart' ] = ""#self.txtGoStart
			message[ 'txtGoEnd' ] = ""#self.txtGoEnd	
			message[ 'txtGoStartCode' ] = ""#self.txtDptRsStn	
			message[ 'txtGoEndCode' ] = ""#self.txtArvRsStn	
			message[ 'selGoYear' ] = "2014"
			message[ 'selGoMonth' ] = "09"
			message[ 'selGoDay' ] = "19"
			message[ 'selGoHour' ] = "19"
			message[ 'txtGoHour' ] = ""
			message[ 'txtGoYoil' ] = ""
			message[ 'selGoSeat1' ] = "15"
			message[ 'selGoSeat2' ] = "15"
			message[ 'txtPsgCnt1' ] = "0"
			message[ 'txtPsgCnt2' ] = "0"
			message[ 'txtGoPage' ] = "1"
			message[ 'txtGoAbrdDt' ] = txtRunDt	
			message[ 'selGoRoom' ] = ""
			message[ 'useSeatFlg' ] = ""
			message[ 'useServiceFlg' ] = ""
			message[ 'checkStnNm' ] = "Y"
			message[ 'SeandYo' ] = ""
			message[ 'txtGoStartCode2' ] = ""
			message[ 'txtGoEndCode2' ] = ""
			message[ 'txtPnrNo' ] = ""
			message[ 'hidStlFlg' ] = ""
			message[ 'chkTrnSeq' ] = ""
			message[ 'chkChgTrn1' ] = ""
			message[ 'chkChgTrn2' ] = ""
			message[ 'chkBtnImgTrn1' ] = ""
			message[ 'chkBtnImgTrn2' ] = ""
			message[ 'chkInitFlg' ] = "Y"
			message[ 'txtMenuId' ] = "11"
			message[ 'ra' ] = "1"
			message[ 'txtSeatAttCd1' ] = "00"
			message[ 'txtSeatAttCd2' ] = self.txtSeatAttCd_2
			message[ 'txtSeatAttCd3' ] = self.txtSeatAttCd_3
			message[ 'txtSeatAttCd4' ] = "15"
			message[ 'txtSeatAttCd5' ] = "00"
			message[ 'strChkCpn' ] = "Y"
			message[ 'txtTotPsgCnt' ] = "1"
			message[ 'txtSrcarCnt' ] = "0"
			message[ 'txtSrcarNo1' ] = ""
			message[ 'txtSrcarNo2' ] = ""
			message[ 'txtSrcarNo3' ] = ""
			message[ 'txtSrcarNo4' ] = ""
			message[ 'txtSrcarNo5' ] = ""
			message[ 'txtSrcarNo6' ] = ""
			message[ 'txtSrcarNo7' ] = ""
			message[ 'txtSrcarNo8' ] = ""
			message[ 'txtSrcarNo9' ] = ""
			message[ 'txtSeatNo1' ] = ""
			message[ 'txtSeatNo2' ] = ""
			message[ 'txtSeatNo3' ] = ""
			message[ 'txtSeatNo4' ] = ""
			message[ 'txtSeatNo5' ] = ""
			message[ 'txtSeatNo6' ] = ""
			message[ 'txtSeatNo7' ] = ""
			message[ 'txtSeatNo8' ] = ""
			message[ 'txtSeatNo9' ] = ""
			message[ 'hidRsvChgNo' ] = ""
			message[ 'hidRsvTpCd' ] = "03"
			message[ 'txtPsgTpCd1' ] = "1"
			message[ 'txtPsgTpCd2' ] = "3"
			message[ 'txtPsgTpCd3' ] = "1"
			message[ 'txtPsgTpCd4' ] = "3"
			message[ 'txtPsgTpCd5' ] = "1"
			message[ 'txtPsgTpCd6' ] = "1"
			message[ 'txtPsgTpCd7' ] = "1"
			message[ 'txtPsgTpCd8' ] = ""
			message[ 'txtPsgTpCd9' ] = ""
			message[ 'txtDiscKndCd1' ] = ""
			message[ 'txtDiscKndCd2' ] = ""
			message[ 'txtDiscKndCd3' ] = "P21"
			message[ 'txtDiscKndCd4' ] = "P21"
			message[ 'txtDiscKndCd5' ] = "P41"
			message[ 'txtDiscKndCd6' ] = "P11"
			message[ 'txtDiscKndCd7' ] = "P22"
			message[ 'txtDiscKndCd8' ] = ""
			message[ 'txtDiscKndCd9' ] = ""
			message[ 'txtCompaCnt1' ] = self.psgCnt
			message[ 'txtCompaCnt2' ] = ""
			message[ 'txtCompaCnt3' ] = ""
			message[ 'txtCompaCnt4' ] = ""
			message[ 'txtCompaCnt5' ] = ""
			message[ 'txtCompaCnt6' ] = ""
			message[ 'txtCompaCnt7' ] = ""
			message[ 'txtCompaCnt8' ] = ""
			message[ 'txtCompaCnt9' ] = ""
			message[ 'txtStndFlg' ] = ""
			message[ 'txtJobId' ] = "1101"
			message[ 'txtJrnyCnt' ] = "1"
			message[ 'txtPsrmClCd1' ] = "1"
			message[ 'txtJrnySqno1' ] = "001"
			message[ 'txtJrnyTpCd1' ] = "11"
			message[ 'txtDptDt1' ] = txtRunDt
			message[ 'txtDptRsStnCd1' ] = self.txtDptRsStn
			message[ 'txtDptTm1' ] = "204000"
			message[ 'txtArvRsStnCd1' ] = self.txtArvRsStn	
			message[ 'txtArvTm1' ] = "223500"
			message[ 'txtTrnNo1' ] = txtTrnNo
			message[ 'txtRunDt1' ] = txtRunDt
			message[ 'txtTrnClsfCd1' ] = self.txtTrnClsfCd1
			message[ 'txtChgFlg1' ] = "N"
			message[ 'txtDoTrnFlg1' ] = "L"
			message[ 'txtPsrmClCd2' ] = ""
			message[ 'txtJrnySqno2' ] = ""
			message[ 'txtJrnyTpCd2' ] = ""
			message[ 'txtDptDt2' ] = ""
			message[ 'txtDptRsStnCd2' ] = ""
			message[ 'txtDptTm2' ] = ""
			message[ 'txtArvRsStnCd2' ] = ""
			message[ 'txtArvTm2' ] = ""
			message[ 'txtTrnNo2' ] = ""
			message[ 'txtRunDt2' ] = ""
			message[ 'txtTrnClsfCd2' ] = ""
			message[ 'txtChgFlg2' ] = ""
			message[ 'txtDoTrnFlg2' ] = ""
			message[ 'selGoStartDay' ] = ""
			message[ 'PageInx' ] = ""
			message[ 'hidEasyTalk' ] = ""


		else :
			message = {}
			message[ 'hidDiscount' ] = ""
			message[ 'selGoTrain' ] = self.selGoTrain # 무궁화: 02
			message[ 'txtPsgFlg_1' ] = "1"
			message[ 'txtPsgFlg_2' ] = "0"
			message[ 'txtPsgFlg_3' ] = "0"
			message[ 'txtPsgFlg_4' ] = "0"			
			message[ 'txtPsgFlg_5' ] = "0"
			message[ 'txtSeatAttCd_3' ] = self.txtSeatAttCd_3 # 무궁화: 11
			message[ 'txtSeatAttCd_2' ] = self.txtSeatAttCd_2 # 무궁화: 00
			message[ 'txtSeatAttCd_4' ] = "15"
			message[ 'selGoTrainRa' ] = self.selGoTrainRa
			message[ 'radJobId' ] = "1"
			message[ 'txtGoStart' ] = ""#self.txtGoStart
			message[ 'txtGoEnd' ] = ""#self.txtGoEnd	
			message[ 'txtGoStartCode' ] = ""#self.txtDptRsStn	
			message[ 'txtGoEndCode' ] = ""#self.txtArvRsStn	
			message[ 'selGoYear' ] = "2015"	
			message[ 'selGoMonth' ] = "01"
			message[ 'selGoDay' ] = "20"	
			message[ 'selGoHour' ] = "00"	
			message[ 'txtGoHour' ] = ""	
			message[ 'txtGoYoil' ] = ""	
			message[ 'selGoSeat1' ] = "15"	
			message[ 'selGoSeat2' ] = "15"	
			message[ 'txtPsgCnt1' ] = "0"		
			message[ 'txtPsgCnt2' ] = "0"		
			message[ 'txtGoPage' ] = "1"		
			message[ 'txtGoAbrdDt' ] = txtRunDt		
			message[ 'selGoRoom' ] = ""		
			message[ 'useSeatFlg' ] = ""	
			message[ 'useServiceFlg' ] = ""	
			message[ 'checkStnNm' ] = "Y"	
			#message[ 'txtMenuId' ] = "11"	
			message[ 'SeandYo' ] = ""	
			message[ 'txtGoStartCode2' ] = ""	
			message[ 'txtGoEndCode2' ] = ""	
			message[ 'selGoStartDay' ] = ""	
			message[ 'txtPnrNo' ] = ""
			message[ 'hidStlFlg' ] = ""
			message[ 'chkTrnSeq' ] = ""	
			message[ 'chkChgTrn1' ] = ""
			message[ 'chkChgTrn2' ] = ""
			message[ 'chkBtnImgTrn1' ] = ""
			message[ 'chkBtnImgTrn2' ] = ""
			message[ 'chkInitFlg' ] = "Y"
			message[ 'txtMenuId' ] = "11"
			message[ 'ra' ] = "1"
			message[ 'txtSeatAttCd1' ] = "00"
			message[ 'txtSeatAttCd2' ] = self.txtSeatAttCd_2
			message[ 'txtSeatAttCd3' ] = self.txtSeatAttCd_3
			message[ 'txtSeatAttCd4' ] = "15"
			message[ 'txtSeatAttCd5' ] = "00"
			message[ 'strChkCpn' ] = "N"
			message[ 'txtTotPsgCnt' ] = "1"
			message[ 'txtSrcarCnt' ] = "0"
			message[ 'txtSrcarNo1' ] = ""
			message[ 'txtSrcarNo2' ] = ""
			message[ 'txtSrcarNo3' ] = ""
			message[ 'txtSrcarNo4' ] = ""
			message[ 'txtSrcarNo5' ] = ""
			message[ 'txtSrcarNo6' ] = ""
			message[ 'txtSrcarNo7' ] = ""
			message[ 'txtSrcarNo8' ] = ""
			message[ 'txtSrcarNo9' ] = ""
			message[ 'txtSeatNo1' ] = ""
			message[ 'txtSeatNo2' ] = ""
			message[ 'txtSeatNo3' ] = ""
			message[ 'txtSeatNo4' ] = ""
			message[ 'txtSeatNo5' ] = ""
			message[ 'txtSeatNo6' ] = ""
			message[ 'txtSeatNo7' ] = ""	
			message[ 'txtSeatNo8' ] = ""
			message[ 'txtSeatNo9' ] = ""
			message[ 'hidRsvChgNo' ] = ""
			message[ 'hidRsvTpCd' ] = "03"
			message[ 'txtPsgTpCd1' ] = "1"	
			message[ 'txtPsgTpCd2' ] = "3"
			message[ 'txtPsgTpCd3' ] = "1"
			message[ 'txtPsgTpCd4' ] = "3"
			message[ 'txtPsgTpCd5' ] = "1"
			message[ 'txtPsgTpCd6' ] = "1"	
			message[ 'txtPsgTpCd7' ] = "1"
			message[ 'txtPsgTpCd8' ] = ""	
			message[ 'txtPsgTpCd9' ] = ""
			message[ 'txtDiscKndCd1' ] = ""
			message[ 'txtDiscKndCd2' ] = ""
			message[ 'txtDiscKndCd3' ] = "P21"
			message[ 'txtDiscKndCd4' ] = "P21"		
			message[ 'txtDiscKndCd5' ] = "P41"
			message[ 'txtDiscKndCd6' ] = "P11"	
			message[ 'txtDiscKndCd7' ] = "P22"
			message[ 'txtDiscKndCd8' ] = ""
			message[ 'txtDiscKndCd9' ] = ""
			message[ 'txtCompaCnt1' ] = self.psgCnt
			message[ 'txtCompaCnt2' ] = "0"		
			message[ 'txtCompaCnt3' ] = "0"
			message[ 'txtCompaCnt4' ] = "0"	
			message[ 'txtCompaCnt5' ] = "0"
			message[ 'txtCompaCnt6' ] = "0"
			message[ 'txtCompaCnt7' ] = "0"
			message[ 'txtCompaCnt8' ] = ""
			message[ 'txtCompaCnt9' ] = ""		
			message[ 'txtStndFlg' ] = ""
			message[ 'txtJobId' ] = "1101"
			message[ 'txtJrnyCnt' ] = "1"		
			message[ 'txtPsrmClCd1' ] = "1"
			message[ 'txtJrnySqno1' ] = "001"	
			message[ 'txtJrnyTpCd1' ] = "11"
			message[ 'txtDptDt1' ] = txtRunDt
			message[ 'txtDptRsStnCd1' ] = self.txtDptRsStn
			message[ 'txtDptTm1' ] = "163000"
			message[ 'txtArvRsStnCd1' ] = self.txtArvRsStn		
			message[ 'txtArvTm1' ] = "182500"
			message[ 'txtTrnNo1' ] = txtTrnNo
			message[ 'txtRunDt1' ] = txtRunDt	
			message[ 'txtTrnClsfCd1' ] = self.txtTrnClsfCd1
			message[ 'txtChgFlg1' ] = "N"	
			message[ 'txtDoTrnFlg1' ] = "" ### 원래 L임
			message[ 'txtPsrmClCd2' ] = ""
			message[ 'txtJrnySqno2' ] = ""
			message[ 'txtJrnyTpCd2' ] = ""
			message[ 'txtDptDt2' ] = ""	
			message[ 'txtDptRsStnCd2' ] = ""		
			message[ 'txtDptTm2' ] = ""
			message[ 'txtArvRsStnCd2' ] = ""	
			message[ 'txtArvTm2' ] = ""
			message[ 'txtTrnNo2' ] = ""
			message[ 'txtRunDt2' ] = ""
			message[ 'txtTrnClsfCd2' ] = ""
			message[ 'txtChgFlg2' ] = ""
			message[ 'txtDoTrnFlg2' ] = ""	
			message[ 'selGoStartDay' ] = ""
			message[ 'txt365Flg' ] = "N"
			message[ 'PageInx' ] = ""
			message[ 'hidEasyTalk' ] = ""	
			
		params = urllib.urlencode( message )

		
		#conn2 = httplib.HTTPConnection( "www.letskorail.com", self.port, timeout=5 )
		conn2 = httplib.HTTPConnection( "www.letskorail.com", timeout=5 )
		
		try : 
			conn2.request( "POST", "/ebizprd/EbizPrdTicketPr12111_i1.do", params, headers )
			response = conn2.getresponse()
			data = response.read()
			res_header = str(response.msg)
			conn2.close()
		except :
			conn2.close()
			return -1

		self.changeCookie( res_header )

			
		if response.status == 200 :
				print "Reservation Completed."
				#print data
				return 0

		elif response.status == 302 :
				print "Reservation Failed. Trying continues."
				
				conn3 = httplib.HTTPSConnection( "www.letskorail.com", timeout=5 )
				conn3.request( "POST", "/docs/pz/Error_pr_1.jsp", params, headers )
				response = conn3.getresponse()
				data = response.read()
				res_header = str(response.msg)
				conn3.close()
				
				documentElement = lxml.html.fromstring( data )
				classMagicName = "guide_msg"
		
				if len( documentElement.find_class( classMagicName ) ) == 0 :
					print "No guide message is available"
					return -1
			
				tableElement = documentElement.find_class( classMagicName )[0]
				print tableElement.text_content()

		
				self.changeCookie( res_header )
			
				return -1
		else :
				print "Reservation Failed: Unknown failure. Aborted."
				print response.status, response.reason
				print response.msg
				print unicode(data)
				return -1

	
	def sendMail( self, data, index ) :
		print "Sending Mail..."

		if self.isBigDiscount == "Y" :
			depTime = "Unknown"
			txtTrnNo = self.trainNo
			txtRunDt = self.resDate	
		else :
			magic = "train\[%d\] = new train_info\(([^)]+)\);" % (index)
			paramsString = re.findall( magic, data )
			trimedParamsString = re.sub(r"\s+", "", paramsString[0])
			items = trimedParamsString.split( ',' )

			depTime = items[5].replace( "\"", "" )
			txtTrnNo = items[6].replace( "\"", "" )
			txtRunDt = items[0].replace( "\"", "" )
		
		
		mailMsg = "Ticket Reserved: %s, %s, %s" % (depTime, txtTrnNo, txtRunDt)
		fromAddr = "" 
		toAddr = "" 
	
		msg = MIMEText( mailMsg )
		msg['Subject'] = mailMsg 
		msg['From'] = fromAddr
		msg['To'] = toAddr
		
		s = smtplib.SMTP_SSL('smtp.gmail.com',465)
		s.login("", "")
		s.sendmail( fromAddr, toAddr, msg.as_string())
		s.quit()
		
		#mailServer = smtplib.SMTP("smtp.gmail.com", 587)
		#mailServer.ehlo()
		#mailServer.starttls()
		#mailServer.ehlo()
		#mailServer.login( "", "" )
		#mailServer.sendmail( fromAddr, toAddr, msg.as_string())
		#mailServer.close()

	def checkTriggerTime( self, txtRunDt ) :
		print "\nTrigger Time for reservation is %s %s" % (txtRunDt, self.triggerTime)
		
		now = time.localtime()
		curDate = "%04d%02d%02d" % (now.tm_year, now.tm_mon, now.tm_mday)
		curTime = "%02d%02d%02d" % (now.tm_hour, now.tm_min, now.tm_sec)
		
		# 한 달이 넘게 남았으면 07:00 기준으로 예매 시도
		# 그렇지 않으면 바로 예매로 수정 필요
		
		if txtRunDt < curDate :
			print "Reservation date is already past! (res: %s, now: %s)"%(txtRunDt, curDate)
			sys.exit(-1)

		if self.triggerTime == None :
			self.triggerTime = "070000"
			
		triggerTimeSec = int(self.triggerTime[:2])*60*60 + int(self.triggerTime[2:4])*60 + int(self.triggerTime[4:6])
		currentTimeSec = now.tm_hour*60*60 + now.tm_min*60 + now.tm_sec
		
		if triggerTimeSec + 60*60 < currentTimeSec :
			print "Trigger time is already past! (trg: %s, now: %s)"%(triggerTimeSect, currentTimeSec)
			sys.exit(-1)
			
		if triggerTimeSec - currentTimeSec > 10 :
			print "%d - 10 seconds is left to start trying reservation" % (triggerTimeSec - currentTimeSec)
			return False
			
		return True
	
	def calculateTimeSkew( self ) :
	
		if len( sys.argv ) is 1 :  # 윈도우 PC
			c = ntplib.NTPClient()
			try :
				response = c.request('0.debian.pool.ntp.org')
			except :
				return False
				
			ntpTime = time.gmtime(response.tx_time + 9*60*60) # KMT
			localTime = time.localtime()
			
			self.timeSkew = int( time.mktime( ntpTime ) ) - int( time.mktime( localTime ) )
		else : # 라즈베리는 NTP 사용
			self.timeSkew = 0
		
		return True
		
	
	def checkTriggerTimeUsingNTP( self, txtRunDt ) :
		
		#if len( sys.argv ) is not 1 :
		#	now = time.localtime()
		#else :
		#	now = time.localtime() + self.timeSkew
		#response = c.request('time.bora.net')
		#now = time.gmtime(response.tx_time)
		
		now = time.localtime()
		
		if self.triggerTime == None :
			self.triggerTime = "070000"

		# 한 달이 넘게 남았으면 07:00 기준으로 예매 시도
		# 그렇지 않으면 바로 예매로 수정 필요
		currentDatetime = datetime.datetime.fromtimestamp( time.mktime( now ) + self.timeSkew )
		currentTimeSec = int( time.mktime( now ) + self.timeSkew )
		dateAfterMonth = datetime.datetime.fromtimestamp( time.mktime( now ) + self.timeSkew )+ relativedelta(months=1)
		dateAfterMonthSec = int( time.mktime( dateAfterMonth.timetuple() ) )
		triggerDatetime = datetime.datetime( int(txtRunDt[:4]), int(txtRunDt[4:6]), int(txtRunDt[6:8]), int(self.triggerTime[:2]), int(self.triggerTime[2:4]))
		triggerTimeSec = int( time.mktime( triggerDatetime.timetuple() ) )
		
		print "Current Time: %s" % (currentDatetime.strftime( '%Y-%m-%d %H:%M:%S' ))
		print "Trigger Time: %s" % (triggerDatetime.strftime( '%Y-%m-%d %H:%M:%S' ) )
		if triggerTimeSec > dateAfterMonthSec + 120 :
			print "Sleeping in %d seconds... %d sec remained\n" % ( triggerTimeSec - dateAfterMonthSec - 120, triggerTimeSec - dateAfterMonthSec )

			self.httpConn.close() # 장시간 sleep 모드로 들어감
			self.httpConn = -1
			time.sleep( triggerTimeSec - dateAfterMonthSec - 120 )
			self.stdout.login() # 새로이 로긴하여 쿠키를 생성
			return False
		elif triggerTimeSec > dateAfterMonthSec + 60 :
			print "Sleeping in %d seconds... %d sec remained\n" % ( 60, triggerTimeSec - dateAfterMonthSec )
			sys.stdout.flush()
			time.sleep( 60 )
			return False
		elif triggerTimeSec > dateAfterMonthSec :
			print "Sleeping in %d seconds... %d sec remained\n" % ( triggerTimeSec - dateAfterMonthSec, triggerTimeSec - dateAfterMonthSec )
			sys.stdout.flush()
			time.sleep( triggerTimeSec - dateAfterMonthSec )
			return True
		elif triggerTimeSec + 5 > dateAfterMonthSec: # 예매시작 후 5초가 지나지 않았을 때
			print "Trigger time is past within 5 secs! Trying reservation!\n"
			sys.stdout.flush()
			return True
		elif triggerTimeSec + 24*60*60 > dateAfterMonthSec: # 예매시작 후 5초 이상 지난 당일
			print "Trigger time is already past! Stop!\n"
			exit( 1 )
		elif triggerTimeSec > currentTimeSec :
			print "Trying reservation!\n"
			sys.stdout.flush()
			return True
		else :	
			print "Trigger time is already past!\n"
			exit( 1 )

			
	def checkTriggerTimeUsingNTPOld( self, txtRunDt ) :
	
		c = ntplib.NTPClient()
		response = c.request('pool.ntp.org')
		now = time.gmtime(response.tx_time + 9*60*60) # KMT 
		#response = c.request('time.bora.net')
		#now = time.gmtime(response.tx_time)
				
		print ctime(response.tx_time)
		curDate = "%04d%02d%02d" % (now.tm_year, now.tm_mon, now.tm_mday)
		curTime = "%02d%02d%02d" % (now.tm_hour, now.tm_min, now.tm_sec)
		print "Now: %s %s" % (curDate, curTime)
		
		if txtRunDt < curDate :
			print "Reservation date is already past!(res: %s, now: %s)"%(txtRunDt, curDate)
			sys.exit(-1)
		
		if self.triggerTime == None :
			self.triggerTime = "070000"
			
		triggerTimeSec = int(self.triggerTime[:2])*60*60 + int(self.triggerTime[2:4])*60 + int(self.triggerTime[4:6])
		currentTimeSec = now.tm_hour*60*60 + now.tm_min*60 + now.tm_sec
		
		if triggerTimeSec + 60*60 < currentTimeSec :
			print "Trigger time is already past! (trg: %s, now: %s)"%(triggerTimeSec, currentTimeSec)
			sys.exit(-1)
			
		#if triggerTimeSec - currentTimeSec > 10 :
		#	print "%d - 10 seconds is left to start trying reservation" % (triggerTimeSec - currentTimeSec)
		#	return False
		if triggerTimeSec > currentTimeSec + 60:
			print "Sleeping in %d seconds... %d sec remained" % ( 60, triggerTimeSec - currentTimeSec )
			sys.stdout.flush()
			time.sleep( 60 )
			return False
		else :
			print "Sleeping in %d seconds... %d sec remained" % ( triggerTimeSec - currentTimeSec, triggerTimeSec - currentTimeSec )
			sys.stdout.flush()
			time.sleep( triggerTimeSec - currentTimeSec )
			return True
		
	def main_loop(self):
		self.login()
	
		while 1:
			if self.isBigDiscount == "Y" :
			
			
				while self.httpConn is -1 :
					data = self.getSchedule() # 예약을 위한 소켓을 미리 만들어 둠
					time.sleep( 1 )
					

			
				self.period = 1
				txtRunDt = self.resDate
				txtTrnNo = self.trainNo
				
				#if self.triggerTime == None or self.checkTriggerTime(txtRunDt) :
				if self.triggerTime == None or self.checkTriggerTimeUsingNTP(txtRunDt) :

					if txtTrnNo != None:
						if self.reserve2( data, -1 ) == 0 :
							if self.sendMailFlag == True :
								self.sendMail( data, -1 )
							sys.exit(0)
					else :
						print "Train number must be given for the bigDiscount reservation"
						sys.exit(-1)
			else :
				data = self.getSchedule()
				
				if data != None :
					index = self.searchSeats( data )
					if index >= 0 :
						if self.reserve2( data, index ) == 0 :
							if self.sendMailFlag == True :
								self.sendMail( data, index )
							sys.exit(0)
				else :
					#self.logout()
					#self.cookieSet = {}
					#self.cookie = ""
					
					#self.login()
					print "No train is availble. Trying Again"
				
			time.sleep( self.period )	
	
if __name__ == '__main__':

	reload(sys)
	sys.setdefaultencoding('utf-8')

	res = Reservation()
	
	res.main_loop()
		

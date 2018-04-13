import requests,re,json,time,os
import pymysql
from urllib.parse import urlencode
from pyquery import PyQuery as pq

#使用数据库
name = 'root'
password = ''  # 替换为自己的账户名和密码
# 建立本地数据库连接(需要先开启数据库服务)
db = pymysql.connect('localhost', name, password, charset='utf8')
cursor = db.cursor()
sqlSentence2 = "use stockDataBase;"
cursor.execute(sqlSentence2)

#得到所有股票的代码
def getcodes():
    url='http://quote.eastmoney.com/stocklist.html'
    i =0
    req =requests.get(url,timeout=30)
    reporthtml=req.text
    html = pq(reporthtml)
    #print(html)
    stock_a_list = html("#quotesearch ul li a[target='_blank']").items()
    codes = []
    for stock_a in stock_a_list:
        num = stock_a.text().split('(')[1].strip(')')
        if  (num.startswith('1') or num.startswith('5')or num.startswith('2')): continue  # 只需要6*/0*/*3/*2
        sname = stock_a.text().split('(')[0]
        record = {}#用于存储个股的代码，和名称

       #****************************************名称编码一直出问题
        sname = sname.encode("iso-8859-1").decode('gbk').encode('utf-8')
        result = str(sname, encoding='utf-8')
        print(result)
        record["sname"]=result
       #********************************************
        record["num"]=num;
        codes.append(record)
        i=i+1
    print(i)
    return  codes

##写入文件
def write_to_json(content,path):
    with open(path,'wb')as f:
        f.write(content)


#得到报道
def getReport():
    codes = getcodes()

    id = 1 ;  # 用于标记该个股的报道条数
    for code in codes:
        #try:
        #个股页面
        url = "http://finance.sina.com.cn/realstock/company/sh" + code["num"] + "/nc.shtml"
        #print(url)
        s_html = requests.get(url,timeout=30).text
        s_doc = pq(s_html)
        #得到个股资讯列表页面
        base = "http://vip.stock.finance.sina.com.cn/corp/view/vCB_AllNewsStock.php?symbol=sh"+code["num"]+"&Page="
        page =1;
        flag =True
        while flag:
            report_urls=base+str(page)
            print(report_urls)
            try:
                report_list_wrap = requests.get(report_urls,timeout=30).text
            except:
                print("url出错了Q!!")
                flag=False
                break;
            if report_list_wrap=='':
                    print("*********************没有下一页了")
                    flag = False
            else:
                page = page+1
                report_list_wrap=pq(report_list_wrap)
                print(report_urls)
                isclose = report_list_wrap("#closed")
                if isclose=="已退市":
                    flag=False;
                    break
                report_list=report_list_wrap("#con02-7 .datelist ul a").items()
                #获得该个股的名称，这里有问题，获得的是乱码
                sname = report_list_wrap("#stockName").text().encode("iso-8859-1").decode('gbk').encode('utf-8')
                sname = str(sname, encoding='utf-8')
                print("名称："+sname)
                print(report_list)
                # **************************************遍历个股的资讯
                for r in report_list:
                    #获取报道标题
                    try:
                        report_title= r.text().encode("iso-8859-1").decode('gbk').encode('utf-8')
                        report_title = str(report_title, encoding='utf-8')
                        print("标题："+report_title)
                        #获取报道链接并得到报道
                        report_url = r.attr("href")
                        req = requests.get(report_url, timeout=30)
                        reporthtml = req.text
                        ##解决编码问题
                        #print(req.encoding)
                        if req.encoding == 'ISO-8859-1':
                            encodings = requests.utils.get_encodings_from_content(req.text)
                            if encodings:
                                encoding = encodings[0]
                            else:
                                encoding = req.apparent_encoding
                        reporthtml = req.content.decode(encoding, 'replace').encode('utf-8', 'replace')
                        reporthtml = pq(reporthtml)
                    except:
                        flag = False
                        print(code['num'] + report_title + "报错了")

                    ##得到日期，如果不是18年的报道则退出该公司报道的爬取，2018年4月2日
                    date = reporthtml(".date").text()
                    if date == '':
                        date = reporthtml('.time-source').text()
                    try:
                        year = int(date[0:4])
                        print(year)
                        if year != 2018:
                            print("年部位2018")
                            flag = False
                            break;
                        month = int(date[5:7])
                        day = int(date[8:10])
                    except Exception as e:
                        print('日期出错:', e)

                    #获取报道日期2018-04-02
                    rdate=date[0:4]+"-"+date[5:7]+"-"+date[8:10]
                    print(rdate)
                    # 获取报道正文
                    content = reporthtml("#artibody").text()
                    #print(code['sname'])
                    #*******************************************插入数据库
                    # [1,600000,白云机场，2018-04-02,，重磅出击百年基础，内容，-2]
                    sql = ("insert into stock(rid,scode,sname,rdate,rtitle,report,emotion) VALUES (%s,%s,%s,%s,%s,%s,%s) ")
                    data_report = (str(id), code['num'], code['sname'],rdate,report_title, content, '-2')
                    id = id + 1
                    try:
                        # 执行sql语句
                        cursor.execute(sql,data_report)
                        print(code['sname']+"插入成功")
                        # 提交到数据库执行
                        db.commit()
                    except Exception as e:
                        print('perhaps timeout:', e)
                        db.rollback()
def main():
    getReport()

if __name__ == '__main__':
    main()

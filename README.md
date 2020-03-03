# corona19-notification
코로나19 현황 메시지를 주기적으로 보내는 프로젝트

<br>

## 특징
- 보건복지부, SBS, NAVER 등 정부기관, 언론 및 포털 등지에서 코로나 현황을 수집하여 알람을 보낸다.

<br>

### 알람 방식
- 기본적으로 알람엔 아래의 정보가 포함되며, 여러 매체의 수치 중 가장 높은 값을 사용한다.
    - 정보 제공 매체
    - 확진자 수
    - 격리해제자 수
    - 사망자 수
- 이외에도 매체별로 추가적인 수집 항목이 있는경우 해당 값도 포함하여 알람을 전송한다.
    - ex) SBS의 경우 신천지 관련 정보 추가 제공

<br>

### 알람 수단
- Line (완성)
- KakaoTalk (예정)
- E-Mail (예정)

<br>

## 예시
![image](https://user-images.githubusercontent.com/20942871/75522755-108f5800-5a4e-11ea-856e-65d0a6691df2.png)


<br>

## 자료 제공 매체
- NAVER: 코로나 검색
- 보건복지부 코로나바이러스감염증-19 현황: http://ncov.mohw.go.kr/index_main.jsp
- SBS 데이터 저널리즘 팀 마부작침: http://mabu.newscloud.sbs.co.kr/202002corona2/

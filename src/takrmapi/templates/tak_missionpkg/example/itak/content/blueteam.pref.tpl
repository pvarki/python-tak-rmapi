<?xml version="1.0" encoding="ASCII" standalone="yes"?>
<preferences>
   <preference version="1" name="cot_streams">
      <entry key="count" class="class java.lang.Integer">1</entry>
      <entry key="description0" class="class java.lang.String">{{ tak_server_name }}</entry>
      <entry key="enabled0" class="class java.lang.Boolean">true</entry>
      <entry key="connectString0" class="class java.lang.String">{{ tak_server_address }}:8089:ssl</entry>
   </preference>
   <preference version="1" name="com.atakmap.app_preferences">
      <entry key="displayServerConnectionWidget" class="class java.lang.Boolean">true</entry>
      <entry key="caLocation" class="class java.lang.String">cert/takserver-public.p12</entry>
      <entry key="caPassword" class="class java.lang.String">public</entry>
      <!-- client certificate should be delivered by other means? -->
      <entry key="certificateLocation" class="class java.lang.String">cert/{{ client_cert_name }}.p12</entry>
      <!-- client_cert_password == callsign == client_cert_name -->
      <entry key="clientPassword" class="class java.lang.String">{{ client_cert_password }}</entry>
   </preference>
</preferences>

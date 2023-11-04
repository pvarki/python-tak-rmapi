<MissionPackageManifest version="2">
   <Configuration>
      <Parameter name="uid" value="{{ tak_server_uid_name }}"/>
      <Parameter name="name" value="{{ tak_server_name }}"/>
      <Parameter name="onReceiveDelete" value="false"/>
   </Configuration>
   <Contents>
      <Content ignore="false" zipEntry="content/blueteam.pref"/>
      <Content ignore="false" zipEntry="content/Google_Hybrid.xml"/>
      <Content ignore="false" zipEntry="content/rasenmaeher_ca-public.p12"/>
      <!-- Client certificates are not delivered within mission package zip -->
      <!-- <Content ignore="false" zipEntry="content/{{ client_cert_name }}.p12"/> -->
      <Content ignore="false" zipEntry="TAK_defaults.pref"/>
   </Contents>
</MissionPackageManifest>

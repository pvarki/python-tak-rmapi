<MissionPackageManifest version="2">
   <Configuration>
      <Parameter name="uid" value="{{ tak_server_uid_name }}"/>
      <Parameter name="name" value="{{ tak_server_name }}"/>
      <Parameter name="onReceiveDelete" value="false"/>
   </Configuration>
   <Contents>
      <Content ignore="false" zipEntry="blueteam.pref"/>
      <Content ignore="false" zipEntry="Google_Hybrid.xml"/>
      <Content ignore="false" zipEntry="rasenmaeher_ca-public.p12"/>
      <Content ignore="false" zipEntry="{{ client_cert_name }}.p12"/>
      <Content ignore="false" zipEntry="TAK_defaults.pref"/>
   </Contents>
</MissionPackageManifest>

<MissionPackageManifest version="2">
   <Configuration>
      <Parameter name="uid" value="{{ tak_server_uid_name }}"/>
      <Parameter name="name" value="{{ tak_server_name }}"/>
      <Parameter name="onReceiveImport" value="true"/>
      <Parameter name="onReceiveDelete" value="false"/>
   </Configuration>
   <Contents>
      <Content ignore="false" zipEntry="server.pref"/>
      <Content ignore="false" zipEntry="rasenmaeher_ca-public.p12"/>
      <Content ignore="false" zipEntry="{{ client_cert_name }}.p12"/>
      <Content ignore="false" zipEntry="content/MML_Peruskartta.xml"/>
      <Content ignore="false" zipEntry="content/MML_Ortoilmakuva.xml"/>
      <Content ignore="false" zipEntry="content/Google_Roadmap.xml"/>
      <Content ignore="false" zipEntry="content/Google_Hybrid.xml"/>
      <Content ignore="false" zipEntry="content/Google_Satellite.xml"/>
   </Contents>
</MissionPackageManifest>

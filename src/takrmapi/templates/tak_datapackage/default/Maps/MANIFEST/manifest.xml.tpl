<MissionPackageManifest version="2">
   <Configuration>
      <!-- FIX UID VALUE -->
      <Parameter name="uid" value="{{ tak_server_uid_name }}"/>
      <Parameter name="onReceiveDelete" value="true"/>
   </Configuration>
   <Contents>
      <Content ignore="false" zipEntry="MML_Peruskartta.xml"/>
      <Content ignore="false" zipEntry="MML_Ortoilmakuva.xml"/>
      <Content ignore="false" zipEntry="Google_Roadmap.xml"/>
      <Content ignore="false" zipEntry="Google_Hybrid.xml"/>
      <Content ignore="false" zipEntry="Google_Satellite.xml"/>
      <Content ignore="false" zipEntry="Map_defaults.pref"/>
   </Contents>
</MissionPackageManifest>

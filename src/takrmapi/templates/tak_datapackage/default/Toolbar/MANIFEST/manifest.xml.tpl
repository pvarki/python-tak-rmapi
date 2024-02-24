<MissionPackageManifest version="2">
   <Configuration>
      <!-- FIX UID VALUE -->
      <Parameter name="uid" value="{{ tak_server_uid_name }}"/>
      <Parameter name="onReceiveDelete" value="true"/>
      <Parameter name="onReceiveImport" value="true"/>
   </Configuration>
   <Contents>
      <!-- Choose which toolbar to use  --> 
      <Content ignore="false" zipEntry="TeamMember_Toolbar.pref"/>
      <!-- <Content ignore="false" zipEntry="TeamLeader_Toolbar.pref"/> -->
   </Contents>
</MissionPackageManifest>

<MissionPackageManifest version="2">
   <Configuration>
      <!-- FIX UID VALUE -->
      <Parameter name="uid" value="{{ tak_server_uid_name }}"/>
      <Parameter name="onReceiveDelete" value="true"/>
      <Parameter name="onReceiveImport" value="true"/>
   </Configuration>
   <Contents>
      <!-- Better scaling for map clarity -->
      <Content ignore="false" zipEntry="Mesh-Encryption-key.pref"/>
   </Contents>
</MissionPackageManifest>

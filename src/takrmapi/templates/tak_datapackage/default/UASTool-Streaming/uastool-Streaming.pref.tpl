<?xml version='1.0' standalone='yes'?>
<preferences>
  <preference version='1' name='com.atakmap.app_preferences'>
    <!-- Streaming settings for uastool -->
    <entry key="uastool.ROUTES_WAYPOINTS_OVERLAY" class="class java.lang.Boolean">true</entry>
    <entry key="uastool.fov_use_dted" class="class java.lang.Boolean">true</entry>
    <entry key="uastool.pref_cot_broadcast" class="class java.lang.Boolean">true</entry>
    <entry key="uastool.pref_broadcast_size" class="class java.lang.String">1920x1080 (high)</entry>
    <entry key="uastool.pref_broadcast_ssl" class="class java.lang.Boolean">true</entry>
    <entry key="uastool.pref_cached_network_endpoints" class="class java.util.HashSet"><element>{{ v.tak_server_public_address }}</element></entry>
    <entry key="uastool.pref_callsign" class="class java.lang.String">UAS-{{ v.client_cert_name }}</entry>
    <entry key="uastool.pref_poi_id_template" class="class java.lang.String">%-POI</entry>
    <entry key="uastool.pref_ui_ar_on" class="class java.lang.Boolean">true</entry>
    <entry key="uastool.pref_ui_dont_show_warning" class="class java.lang.Boolean">true</entry>
    <!-- Set bitrate with broadcasta size, so there is enough bandwidht -->
    <entry key="uastool.pref_video_broadcast_bitrate" class="class java.lang.String">100000</entry>
    <entry key="uastool.pref_video_broadcast_destination" class="class java.lang.String">SRT (Video Management System)</entry>
    <entry key="uastool.pref_video_observer_url" class="class java.lang.String">rtsps://{{ v.mmtx_server_public_address }}:{{ v.mmtx_server_observer_port }}/live/uas/{{ v.client_cert_name }}?tcp</entry>
    <entry key="uastool.pref_srt_dest_host" class="class java.lang.String">{{ v.mmtx_server_public_address }}</entry>
    <entry key="uastool.pref_srt_dest_port" class="class java.lang.String">{{ v.mmtx_server_srt_port }}</entry>
    <entry key="uastool.pref_srt_stream_id" class="class java.lang.String">publish:live/uas/{{ v.client_cert_name }}:USERNAME:PASSWORD</entry>
        <!-- Input users correct mtx username and password keywords ie. {{ client_mtx_username }} and {{ client_mtx_password }} -->
    <!-- <entry key="uastool.pref_srt_passphrase" class="class java.lang.String">testitestitesti</entry> -->
  </preference>
</preferences>

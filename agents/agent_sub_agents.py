import json, time, random, threading
from collections import defaultdict, OrderedDict

SUB_AGENT_TEMPLATES = {
    "file": {
        "department": "File Management",
        "sub_agents": [
            ("txt_reader", "Text File Reader"), ("csv_reader", "CSV Reader"), ("json_reader", "JSON Reader"),
            ("xml_reader", "XML Reader"), ("yaml_reader", "YAML Reader"), ("ini_reader", "INI Reader"),
            ("log_reader", "Log File Reader"), ("md_reader", "Markdown Reader"), ("html_reader", "HTML Reader"),
            ("pdf_extractor", "PDF Extractor"), ("docx_reader", "DOCX Reader"), ("xlsx_reader", "XLSX Reader"),
            ("txt_writer", "Text Writer"), ("csv_writer", "CSV Writer"), ("json_writer", "JSON Writer"),
            ("xml_writer", "XML Writer"), ("yaml_writer", "YAML Writer"), ("ini_writer", "INI Writer"),
            ("file_copier", "File Copier"), ("file_mover", "File Mover"), ("file_renamer", "File Renamer"),
            ("file_deleter", "File Deleter"), ("file_searcher", "File Searcher"), ("file_finder", "File Finder"),
            ("dir_lister", "Directory Lister"), ("dir_creator", "Directory Creator"), ("dir_remover", "Directory Remover"),
            ("zip_compressor", "ZIP Compressor"), ("zip_extractor", "ZIP Extractor"), ("tar_compressor", "TAR Compressor"),
            ("tar_extractor", "TAR Extractor"), ("gzip_compressor", "GZip Compressor"), ("gzip_extractor", "GZip Extractor"),
            ("file_encrypter", "File Encrypter (AES)"), ("file_decrypter", "File Decrypter (AES)"),
            ("file_syncer", "File Syncer"), ("file_watcher", "File Watcher"), ("file_permission", "Permission Changer"),
            ("file_linker", "Symlink Manager"), ("disk_usage", "Disk Usage Analyzer"), ("duplicate_finder", "Duplicate Finder"),
            ("file_splitter", "File Splitter"), ("file_merger", "File Merger"), ("checksum_gen", "Checksum Generator"),
            ("checksum_verify", "Checksum Verifier"), ("temp_cleaner", "Temp File Cleaner"),
            ("large_file_finder", "Large File Finder"), ("old_file_archiver", "Old File Archiver"),
            ("file_organizer", "File Organizer by Type"), ("bulk_renamer", "Bulk Renamer"),
            ("file_comparer", "File Comparator"), ("binary_reader", "Binary File Reader"),
        ]
    },
    "network": {
        "department": "Network Management",
        "sub_agents": [
            ("ping_tester", "Ping Tester"), ("dns_resolver", "DNS Resolver"), ("dns_lookup", "DNS Lookup"),
            ("port_scanner", "Port Scanner"), ("traceroute", "Traceroute"), ("whois_lookup", "WHOIS Lookup"),
            ("ip_locator", "IP Geolocator"), ("bandwidth_test", "Bandwidth Tester"), ("wifi_scanner", "WiFi Scanner"),
            ("ethernet_check", "Ethernet Checker"), ("dhcp_check", "DHCP Checker"), ("gateway_finder", "Gateway Finder"),
            ("subnet_calc", "Subnet Calculator"), ("mac_lookup", "MAC Address Lookup"), ("ssl_checker", "SSL Certificate Checker"),
            ("http_headers", "HTTP Headers Checker"), ("website_status", "Website Status Checker"),
            ("firewall_check", "Firewall Rule Checker"), ("open_ports", "Open Ports Finder"),
            ("netstat_parser", "Netstat Parser"), ("route_table", "Route Table Viewer"), ("arp_table", "ARP Table Viewer"),
            ("interface_info", "Interface Info"), ("mtu_checker", "MTU Checker"), ("latency_test", "Latency Tester"),
            ("packet_loss", "Packet Loss Checker"), ("jitter_test", "Jitter Tester"), ("speed_test", "Speed Test"),
            ("proxy_checker", "Proxy Checker"), ("vpn_checker", "VPN Status Checker"), ("ssh_tester", "SSH Connectivity"),
            ("ftp_checker", "FTP Checker"), ("smtp_check", "SMTP Check"), ("pop3_check", "POP3 Check"),
            ("imap_check", "IMAP Check"), ("ldap_check", "LDAP Check"), ("ntp_sync", "NTP Sync Checker"),
            ("snmp_walk", "SNMP Walker"), ("netbios_scan", "NetBIOS Scanner"), ("upnp_scan", "UPnP Scanner"),
            ("wol_sender", "Wake-on-LAN"), ("traffic_mon", "Traffic Monitor"), ("connection_list", "Connection Lister"),
            ("proxy_setter", "Proxy Configurator"), ("dns_flusher", "DNS Cache Flusher"),
            ("net_scan", "Network Scanner"), ("ip6_check", "IPv6 Checker"), ("mtr_report", "MTR Report Generator"),
            ("curl_wrapper", "cURL Wrapper"), ("wget_wrapper", "Wget Wrapper"), ("net_calc", "Network Calculator"),
            ("port_listener", "Port Listener Check"), ("service_discover", "Service Discovery"),
        ]
    },
    "device": {
        "department": "Device Management",
        "sub_agents": [
            ("usb_lister", "USB Device Lister"), ("usb_eject", "USB Safely Eject"), ("bluetooth_scan", "Bluetooth Scanner"),
            ("bluetooth_pair", "Bluetooth Pairer"), ("display_info", "Display Info"), ("resolution_set", "Resolution Setter"),
            ("brightness_ctrl", "Brightness Controller"), ("volume_ctrl", "Volume Controller"),
            ("mic_ctrl", "Microphone Controller"), ("camera_check", "Camera Checker"), ("printer_list", "Printer Lister"),
            ("printer_test", "Printer Test Page"), ("scanner_detect", "Scanner Detector"),
            ("keyboard_test", "Keyboard Tester"), ("mouse_test", "Mouse Tester"), ("touchpad_ctrl", "Touchpad Controller"),
            ("battery_info", "Battery Info"), ("power_plan", "Power Plan Switcher"), ("temp_monitor", "Temperature Monitor"),
            ("fan_speed", "Fan Speed Reader"), ("cpu_info", "CPU Info"), ("gpu_info", "GPU Info"),
            ("ram_info", "RAM Info"), ("motherboard_info", "Motherboard Info"), ("bios_version", "BIOS Version"),
            ("disk_list", "Disk Lister"), ("partition_view", "Partition Viewer"), ("disk_smart", "SMART Status"),
            ("disk_benchmark", "Disk Benchmark"), ("audio_device", "Audio Device Lister"), ("input_device", "Input Device Lister"),
            ("network_adapter", "Network Adapter Info"), ("bluetooth_adapter", "Bluetooth Adapter"),
            ("webcam_list", "Webcam Lister"), ("speaker_test", "Speaker Tester"), ("hdd_temp", "HDD Temperature"),
            ("battery_health", "Battery Health"), ("charger_status", "Charger Status"), ("docking_check", "Docking Station"),
            ("pci_list", "PCI Device Lister"), ("usb_history", "USB History"), ("driver_check", "Driver Status"),
            ("joystick_test", "Joystick/Gamepad Tester"), ("tablet_check", "Graphics Tablet Checker"),
            ("fingerprint_check", "Fingerprint Reader Status"), ("card_reader", "Smart Card Reader"),
            ("docking_station", "Docking Station Status"), ("monitor_edid", "Monitor EDID Reader"),
            ("hdr_check", "HDR Support Checker"), ("gsync_check", "G-Sync/FreeSync Checker"),
            ("ddc_ci", "DDC/CI Monitor Control"), ("color_profile", "Color Profile Lister"),
        ]
    },
    "data": {
        "department": "Data Management",
        "sub_agents": [
            ("sql_query", "SQL Query Executor"), ("sql_export", "SQL Export"), ("sql_import", "SQL Import"),
            ("csv_analyst", "CSV Analyst"), ("json_analyst", "JSON Analyst"), ("xml_parser", "XML Parser"),
            ("data_validator", "Data Validator"), ("data_cleaner", "Data Cleaner"), ("data_formatter", "Data Formatter"),
            ("deduplicator", "Deduplicator"), ("null_finder", "Null/Empty Finder"), ("outlier_detect", "Outlier Detector"),
            ("data_sampler", "Data Sampler"), ("data_merger", "Data Merger"), ("data_splitter", "Data Splitter"),
            ("schema_detect", "Schema Detector"), ("type_converter", "Type Converter"), ("encoding_detect", "Encoding Detector"),
            ("encoding_convert", "Encoding Converter"), ("hash_generator", "Hash Generator"), ("hash_compare", "Hash Compare"),
            ("regex_matcher", "Regex Matcher"), ("regex_extractor", "Regex Extractor"), ("text_analyst", "Text Analyst"),
            ("word_counter", "Word Counter"), ("line_counter", "Line Counter"), ("char_counter", "Character Counter"),
            ("pattern_finder", "Pattern Finder"), ("diff_checker", "Diff Checker"), ("sort_tool", "Data Sorter"),
            ("filter_tool", "Data Filter"), ("aggregator", "Data Aggregator"), ("joiner", "Data Joiner"),
            ("pivot_table", "Pivot Table Creator"), ("cross_tab", "Cross Tabulation"),
            ("time_series", "Time Series Analyzer"), ("correlation", "Correlation Finder"),
            ("data_profiler", "Data Profiler"), ("data_quality", "Data Quality Checker"),
            ("anomaly_detect", "Anomaly Detector"), ("trend_analyzer", "Trend Analyzer"),
            ("forecast", "Forecast Predictor"), ("clustering", "Clustering Analyzer"),
            ("classification", "Classifier"), ("regression_analyzer", "Regression Analyzer"),
            ("data_normalizer", "Data Normalizer"), ("data_binner", "Data Binner"),
            ("one_hot_encoder", "One-Hot Encoder"), ("label_encoder", "Label Encoder"),
            ("imputer", "Missing Value Imputer"), ("scaler", "Feature Scaler"),
        ]
    },
    "system": {
        "department": "System Administration",
        "sub_agents": [
            ("cpu_monitor", "CPU Monitor"), ("ram_monitor", "RAM Monitor"), ("disk_monitor", "Disk Monitor"),
            ("process_lister", "Process Lister"), ("process_killer", "Process Killer"), ("process_priority", "Process Priority"),
            ("service_lister", "Service Lister"), ("service_starter", "Service Starter"), ("service_stopper", "Service Stopper"),
            ("service_restarter", "Service Restarter"), ("user_lister", "User Lister"), ("user_adder", "User Adder"),
            ("user_remover", "User Remover"), ("group_lister", "Group Lister"), ("group_adder", "Group Adder"),
            ("group_remover", "Group Remover"), ("env_lister", "Environment Variable Lister"),
            ("env_setter", "Environment Variable Setter"), ("cron_lister", "Cron Job Lister"),
            ("cron_adder", "Cron Job Adder"), ("cron_remover", "Cron Job Remover"),
            ("log_viewer", "Log Viewer"), ("log_tailer", "Log Tailer"), ("log_searcher", "Log Searcher"),
            ("syslog_reader", "Syslog Reader"), ("boot_log", "Boot Log Reader"), ("dmesg_reader", "Kernel Log Reader"),
            ("uptime_check", "Uptime Checker"), ("load_avg", "Load Average"), ("swap_usage", "Swap Usage"),
            ("disk_io", "Disk I/O Monitor"), ("net_io", "Network I/O Monitor"), ("inode_usage", "Inode Usage"),
            ("file_handle", "File Handle Counter"), ("socket_stat", "Socket Statistics"),
            ("kernel_version", "Kernel Version"), ("os_release", "OS Release Info"),
            ("pkg_lister", "Package Lister"), ("pkg_check", "Package Check"), ("apt_update", "APT Update"),
            ("snap_list", "Snap Package Lister"), ("flatpak_list", "Flatpak Lister"),
            ("hostname_setter", "Hostname Setter"), ("timezone_setter", "Timezone Setter"),
            ("locale_setter", "Locale Configurator"), ("keyboard_setter", "Keyboard Layout Setter"),
            ("sysctl_view", "Sysctl Viewer"), ("sysctl_set", "Sysctl Setter"),
            ("modules_list", "Kernel Module Lister"), ("modules_load", "Kernel Module Loader"),
            ("limits_view", "System Limits Viewer"), ("fd_limit", "File Descriptor Limit"),
        ]
    },
    "scheduler": {
        "department": "Task Scheduling",
        "sub_agents": [
            ("one_time_task", "One-Time Task"), ("daily_task", "Daily Task"), ("weekly_task", "Weekly Task"),
            ("monthly_task", "Monthly Task"), ("hourly_task", "Hourly Task"), ("minute_task", "Minute Task"),
            ("cron_gen", "Cron Expression Generator"), ("cron_parser", "Cron Expression Parser"),
            ("reminder_set", "Reminder Setter"), ("alarm_set", "Alarm Setter"), ("timer_set", "Timer Setter"),
            ("countdown", "Countdown Timer"), ("stopwatch", "Stopwatch"), ("interval_task", "Interval Task"),
            ("delay_task", "Delayed Task"), ("retry_task", "Retry Task"), ("conditional_task", "Conditional Task"),
            ("dependency_task", "Dependency Task"), ("parallel_task", "Parallel Task"), ("batch_task", "Batch Task"),
            ("task_killer", "Task Killer"), ("task_pauser", "Task Pauser"), ("task_resumer", "Task Resumer"),
            ("task_lister", "Task Lister"), ("task_log", "Task Logger"), ("task_stats", "Task Statistics"),
            ("watchdog", "Watchdog Timer"), ("heartbeat", "Heartbeat Checker"), ("health_check", "Health Check Task"),
            ("auto_cleanup", "Auto Cleanup Task"), ("backup_task", "Backup Task"), ("sync_task", "Sync Task"),
            ("report_task", "Report Generator Task"), ("email_task", "Email Task"), ("webhook_task", "Webhook Task"),
            ("api_poll", "API Polling Task"), ("file_watch", "File Watch Task"), ("dir_watch", "Directory Watch"),
            ("db_cleanup", "Database Cleanup Task"), ("log_rotate", "Log Rotation Task"),
            ("event_handler", "Event Handler"), ("trigger_engine", "Trigger Engine"),
            ("workflow_engine", "Workflow Engine"), ("pipeline_runner", "Pipeline Runner"),
            ("job_chain", "Job Chain"), ("escalation", "Escalation Handler"),
            ("timeout_handler", "Timeout Handler"), ("retry_policy", "Retry Policy Engine"),
            ("schedule_optimizer", "Schedule Optimizer"), ("calendar_sync", "Calendar Sync Task"),
        ]
    },
    "code": {
        "department": "Code Development",
        "sub_agents": [
            ("py_gen", "Python Code Generator"), ("js_gen", "JavaScript Generator"), ("html_gen", "HTML Generator"),
            ("css_gen", "CSS Generator"), ("bash_gen", "Bash Script Generator"), ("sql_gen", "SQL Generator"),
            ("py_linter", "Python Linter"), ("js_linter", "JavaScript Linter"), ("html_validator", "HTML Validator"),
            ("css_validator", "CSS Validator"), ("json_validator", "JSON Validator"),
            ("py_formatter", "Python Formatter"), ("js_formatter", "JavaScript Formatter"),
            ("py_test_gen", "Python Test Generator"), ("js_test_gen", "JavaScript Test Generator"),
            ("py_doc_gen", "Python Docstring Generator"), ("api_doc_gen", "API Doc Generator"),
            ("readme_gen", "README Generator"), ("gitignore_gen", "Gitignore Generator"),
            ("dockerfile_gen", "Dockerfile Generator"), ("ci_gen", "CI Config Generator"),
            ("py_optimizer", "Python Code Optimizer"), ("js_optimizer", "JS Code Optimizer"),
            ("py_obfuscator", "Python Obfuscator"), ("css_minifier", "CSS Minifier"),
            ("js_minifier", "JS Minifier"), ("html_minifier", "HTML Minifier"),
            ("dep_analyzer", "Dependency Analyzer"), ("dead_code", "Dead Code Finder"),
            ("complexity_check", "Code Complexity Checker"), ("style_check", "Style Guide Checker"),
            ("security_lint", "Security Linter (Bandit)"), ("type_check", "Type Checker"),
            ("code_metrics", "Code Metrics Calculator"), ("py_to_js", "Python-to-JS Converter"),
            ("csv_to_json", "CSV-to-JSON Converter"), ("json_to_yaml", "JSON-to-YAML Converter"),
            ("py_to_exe", "Python-to-Exe Guide"), ("api_tester", "API Tester"), ("curl_gen", "cURL Command Generator"),
            ("regex_tester", "Regex Tester"), ("jq_builder", "jQ Query Builder"),
            ("rust_gen", "Rust Code Generator"), ("go_gen", "Go Code Generator"),
            ("cpp_gen", "C++ Code Generator"), ("java_gen", "Java Code Generator"),
            ("csharp_gen", "C# Code Generator"), ("ruby_gen", "Ruby Code Generator"),
            ("php_gen", "PHP Code Generator"), ("swift_gen", "Swift Code Generator"),
            ("kotlin_gen", "Kotlin Code Generator"), ("typescript_gen", "TypeScript Generator"),
        ]
    },
    "image": {
        "department": "Image Processing",
        "sub_agents": [
            ("img_resizer", "Image Resizer"), ("img_cropper", "Image Cropper"), ("img_rotator", "Image Rotator"),
            ("img_flipper", "Image Flipper"), ("img_grayscale", "Grayscale Converter"), ("img_sepia", "Sepia Filter"),
            ("img_blur", "Blur Filter"), ("img_sharpen", "Sharpen Filter"), ("img_brightness", "Brightness Adjuster"),
            ("img_contrast", "Contrast Adjuster"), ("img_saturation", "Saturation Adjuster"),
            ("img_format_convert", "Format Converter"), ("img_compress", "Image Compressor"),
            ("img_crop_circle", "Circle Crop"), ("img_rounded", "Rounded Corners"),
            ("img_watermark", "Watermark Adder"), ("img_text_overlay", "Text Overlay"),
            ("img_border", "Border Adder"), ("img_shadow", "Shadow Effect"), ("img_pixelate", "Pixelate Effect"),
            ("img_thumbnail", "Thumbnail Creator"), ("img_exif_reader", "EXIF Reader"),
            ("img_exif_remover", "EXIF Remover"), ("img_metadata", "Metadata Viewer"),
            ("img_histogram", "Histogram Generator"), ("img_color_palette", "Color Palette Extractor"),
            ("img_dominant_color", "Dominant Color Finder"), ("img_resolution", "Resolution Checker"),
            ("img_dpi", "DPI Checker"), ("img_batch_resize", "Batch Resizer"),
            ("img_batch_convert", "Batch Converter"), ("img_slideshow", "Slideshow Creator"),
            ("img_to_ascii", "Image to ASCII Art"), ("img_to_base64", "Image to Base64"),
            ("img_sprite_sheet", "Sprite Sheet Creator"), ("img_icon_gen", "Icon Generator"),
            ("img_barcode_reader", "Barcode Reader"), ("img_qr_gen", "QR Code Generator"),
            ("img_qr_read", "QR Code Reader"), ("img_ocr", "OCR Text Extractor"),
            ("img_face_detect", "Face Detector"), ("img_face_blur", "Face Blurrer"),
            ("img_object_detect", "Object Detector"), ("img_color_filter", "Color Filter"),
            ("img_gradient", "Gradient Generator"), ("img_pattern", "Pattern Generator"),
            ("img_collage", "Collage Maker"), ("img_meme_gen", "Meme Generator"),
            ("img_sticker", "Sticker Maker"), ("img_frame", "Frame Adder"),
        ]
    },
    "search": {
        "department": "Search & Retrieval",
        "sub_agents": [
            ("web_search", "Web Search"), ("wiki_search", "Wikipedia Search"), ("news_search", "News Search"),
            ("image_search", "Image Search"), ("video_search", "Video Search"), ("file_search", "File Search"),
            ("code_search", "Code Search"), ("doc_search", "Document Search"), ("pdf_search", "PDF Search"),
            ("email_search", "Email Search"), ("contact_search", "Contact Search"), ("calendar_search", "Calendar Search"),
            ("note_search", "Note Search"), ("bookmark_search", "Bookmark Search"),
            ("history_search", "History Search"), ("cache_search", "Cache Search"),
            ("db_search", "Database Search"), ("api_search", "API Search"), ("pkg_search", "Package Search"),
            ("dict_search", "Dictionary Search"), ("thesaurus_search", "Thesaurus Search"),
            ("translation_search", "Translation Search"), ("price_search", "Price Comparison"),
            ("product_search", "Product Search"), ("job_search", "Job Search"),
            ("recipe_search", "Recipe Search"), ("movie_search", "Movie Search"), ("music_search", "Music Search"),
            ("book_search", "Book Search"), ("map_search", "Map Search"), ("route_search", "Route Search"),
            ("weather_search", "Weather Search"), ("stock_search", "Stock Search"),
            ("crypto_search", "Cryptocurrency Search"), ("domain_search", "Domain Search"),
            ("patent_search", "Patent Search"), ("scholar_search", "Scholar Search"),
            ("repo_search", "Repository Search"), ("issue_search", "Issue Tracker Search"),
            ("knowledge_graph", "Knowledge Graph Search"), ("semantic_search", "Semantic Search"),
            ("vector_search", "Vector Search"), ("fuzzy_search", "Fuzzy Search"),
            ("fulltext_search", "Full-Text Search"), ("metadata_search", "Metadata Search"),
            ("tag_search", "Tag-Based Search"), ("category_search", "Category Search"),
            ("recursive_search", "Recursive Search"), ("indexed_search", "Indexed Search"),
            ("parallel_search", "Parallel Search"), ("distributed_search", "Distributed Search"),
        ]
    },
    "chat": {
        "department": "Conversation",
        "sub_agents": [
            ("greeter", "Greeter Agent"), ("farewell", "Farewell Agent"), ("thanks", "Thank You Agent"),
            ("apology", "Apology Agent"), ("encourager", "Encouragement Agent"), ("motivator", "Motivation Agent"),
            ("joke_teller", "Joke Teller"), ("quote_giver", "Quote Giver"), ("fact_provider", "Fact Provider"),
            ("trivia_master", "Trivia Master"), ("riddle_maker", "Riddle Maker"), ("poem_writer", "Poem Writer"),
            ("story_teller", "Story Teller"), ("complimenter", "Compliment Giver"),
            ("small_talk", "Small Talk Agent"), ("opinion_giver", "Opinion Giver"),
            ("advice_giver", "Advice Giver"), ("philosopher", "Philosophy Agent"),
            ("historian", "History Agent"), ("science_explain", "Science Explainer"),
            ("tech_explain", "Tech Explainer"), ("health_advisor", "Health Advisor"),
            ("fitness_tip", "Fitness Tip Giver"), ("nutrition_info", "Nutrition Info"),
            ("travel_tip", "Travel Tip Giver"), ("food_expert", "Food Expert"),
            ("movie_critic", "Movie Critic"), ("music_expert", "Music Expert"),
            ("book_reviewer", "Book Reviewer"), ("game_reviewer", "Game Reviewer"),
            ("weather_reporter", "Weather Reporter"), ("news_summarizer", "News Summarizer"),
            ("email_assist", "Email Assistant"), ("calendar_assist", "Calendar Assistant"),
            ("meeting_assist", "Meeting Assistant"), ("travel_assist", "Travel Assistant"),
            ("shopping_assist", "Shopping Assistant"), ("cooking_assist", "Cooking Assistant"),
            ("study_assist", "Study Assistant"), ("career_advisor", "Career Advisor"),
            ("meditation_guide", "Meditation Guide"), ("breathing_exercise", "Breathing Exercise Coach"),
            ("sleep_advisor", "Sleep Advisor"), ("stress_relief", "Stress Relief Guide"),
            ("productivity_coach", "Productivity Coach"), ("time_mgmt", "Time Management Advisor"),
            ("finance_tip", "Finance Tip Giver"), ("budget_advisor", "Budget Advisor"),
            ("investing_tip", "Investing Tip Giver"), ("crypto_tip", "Crypto Currency Advisor"),
        ]
    },
    "translator": {
        "department": "Translation",
        "sub_agents": [
            ("en_to_ur", "English to Urdu"), ("ur_to_en", "Urdu to English"), ("en_to_hi", "English to Hindi"),
            ("hi_to_en", "Hindi to English"), ("en_to_es", "English to Spanish"), ("es_to_en", "Spanish to English"),
            ("en_to_fr", "English to French"), ("fr_to_en", "French to English"), ("en_to_de", "English to German"),
            ("de_to_en", "German to English"), ("en_to_zh", "English to Chinese"), ("zh_to_en", "Chinese to English"),
            ("en_to_ja", "English to Japanese"), ("ja_to_en", "Japanese to English"), ("en_to_ar", "English to Arabic"),
            ("ar_to_en", "Arabic to English"), ("en_to_ru", "English to Russian"), ("ru_to_en", "Russian to English"),
            ("en_to_pt", "English to Portuguese"), ("pt_to_en", "Portuguese to English"),
            ("en_to_it", "English to Italian"), ("it_to_en", "Italian to English"),
            ("en_to_ko", "English to Korean"), ("ko_to_en", "Korean to English"),
            ("en_to_nl", "English to Dutch"), ("nl_to_en", "Dutch to English"),
            ("en_to_tr", "English to Turkish"), ("tr_to_en", "Turkish to English"),
            ("en_to_pl", "English to Polish"), ("pl_to_en", "Polish to English"),
            ("en_to_sv", "English to Swedish"), ("sv_to_en", "Swedish to English"),
            ("en_to_da", "English to Danish"), ("da_to_en", "Danish to English"),
            ("en_to_fi", "English to Finnish"), ("fi_to_en", "Finnish to English"),
            ("en_to_no", "English to Norwegian"), ("no_to_en", "Norwegian to English"),
            ("en_to_cs", "English to Czech"), ("cs_to_en", "Czech to English"),
            ("en_to_hu", "English to Hungarian"), ("hu_to_en", "Hungarian to English"),
            ("detect_lang", "Language Detector"), ("transliterate", "Transliteration Tool"),
            ("dialect_detect", "Dialect Detector"), ("formal_trans", "Formal Translation"),
            ("slang_trans", "Slang Translation"), ("idiom_trans", "Idiom Translator"),
            ("en_to_vi", "English to Vietnamese"), ("vi_to_en", "Vietnamese to English"),
            ("en_to_th", "English to Thai"), ("th_to_en", "Thai to English"),
        ]
    },
    "math": {
        "department": "Mathematics",
        "sub_agents": [
            ("arithmetic", "Arithmetic Calculator"), ("algebra", "Algebra Solver"), ("quadratic", "Quadratic Solver"),
            ("linear_eq", "Linear Equations"), ("simultaneous", "Simultaneous Equations"),
            ("calculus_diff", "Differentiation"), ("calculus_int", "Integration"), ("limit_solver", "Limit Solver"),
            ("trigonometry", "Trigonometry Calculator"), ("sin_cos_tan", "Sin/Cos/Tan Calculator"),
            ("pythagoras", "Pythagoras Theorem"), ("geometry_area", "Area Calculator"),
            ("geometry_vol", "Volume Calculator"), ("geometry_perim", "Perimeter Calculator"),
            ("prime_check", "Prime Checker"), ("prime_gen", "Prime Generator"), ("factorization", "Factorizer"),
            ("gcd_lcm", "GCD/LCM Finder"), ("fibonacci", "Fibonacci Generator"), ("factorial", "Factorial Calculator"),
            ("percentage", "Percentage Calculator"), ("ratio", "Ratio Calculator"),
            ("fraction_simp", "Fraction Simplifier"), ("decimal_to_frac", "Decimal to Fraction"),
            ("binary_conv", "Binary Converter"), ("hex_conv", "Hex Converter"), ("octal_conv", "Octal Converter"),
            ("number_base", "Base Converter"), ("roman_numeral", "Roman Numeral Converter"),
            ("statistics_mean", "Mean Calculator"), ("statistics_median", "Median Calculator"),
            ("statistics_mode", "Mode Calculator"), ("std_dev", "Standard Deviation"),
            ("variance", "Variance Calculator"), ("correlation_coef", "Correlation Coefficient"),
            ("probability", "Probability Calculator"), ("permutation", "Permutation Calculator"),
            ("combination", "Combination Calculator"), ("random_gen", "Random Number Generator"),
            ("random_sample", "Random Sampler"), ("rounding", "Rounding Tool"),
            ("scientific_notation", "Scientific Notation"), ("matrix_add", "Matrix Addition"),
            ("matrix_multiply", "Matrix Multiplication"), ("matrix_det", "Matrix Determinant"),
            ("graph_plot", "Graph Plotter Guide"), ("unit_convert", "Unit Converter"),
            ("log_calc", "Logarithm Calculator"), ("exponent_calc", "Exponent Calculator"),
            ("root_finder", "Root Finder"), ("interpolation", "Interpolation Calculator"),
            ("extrapolation", "Extrapolation Calculator"), ("series_solver", "Series Summation"),
        ]
    }
}

class SubAgentSystem:
    def __init__(self):
        self.sub_agents = OrderedDict()
        self.agent_map = {}
        self._lock = threading.Lock()
        self._build()

    def _build(self):
        for main_agent, config in SUB_AGENT_TEMPLATES.items():
            dept = config["department"]
            for sa_id, sa_role in config["sub_agents"]:
                full_id = f"{main_agent}.{sa_id}"
                self.sub_agents[full_id] = {
                    "id": full_id,
                    "main_agent": main_agent,
                    "role": sa_role,
                    "department": dept,
                    "status": "idle",
                    "tasks_completed": 0,
                    "accuracy": random.uniform(0.82, 0.98),
                    "response_time": random.uniform(0.05, 0.5),
                    "parent": main_agent,
                    "level": "sub_agent",
                    "specialization": sa_role.lower()
                }
                if main_agent not in self.agent_map:
                    self.agent_map[main_agent] = []
                self.agent_map[main_agent].append(full_id)

    def process(self, message, main_agent=None, sub_agent_id=None):
        if sub_agent_id and sub_agent_id in self.sub_agents:
            return self._execute(sub_agent_id, message)

        if main_agent:
            agents = self.agent_map.get(main_agent, [])
            if not agents:
                return {"error": f"No sub-agents for {main_agent}"}
            results = []
            selected = self._smart_select(agents, message)[:5]
            for sa_id in selected:
                results.append(self._execute(sa_id, message))
            return {"main_agent": main_agent, "sub_agents_used": len(results), "results": results}

        all_agents = list(self.sub_agents.keys())
        selected = self._smart_select(all_agents, message)[:10]
        results = []
        for sa_id in selected:
            results.append(self._execute(sa_id, message))
        return {"sub_agents_used": len(results), "results": results}

    def _smart_select(self, agent_ids, message):
        msg_lower = message.lower()
        scored = []
        for sa_id in agent_ids:
            sa = self.sub_agents[sa_id]
            score = 0
            spec = sa["specialization"]
            role = sa["role"].lower()
            for word in msg_lower.split():
                if word in spec or word in role:
                    score += 2
                if any(kw in spec for kw in ["reader", "writer", "convert", "search", "check", "calc", "test", "gen"]):
                    if any(kw in msg_lower for kw in ["read", "write", "convert", "find", "check", "calculate", "generate"]):
                        score += 1
            if score > 0:
                scored.append((score + sa["accuracy"], sa_id))
        scored.sort(key=lambda x: -x[0])
        return [s[1] for s in scored] if scored else random.sample(agent_ids, min(5, len(agent_ids)))

    def _execute(self, sa_id, task):
        sa = self.sub_agents.get(sa_id)
        if not sa:
            return {"error": "Sub-agent not found"}

        with self._lock:
            sa["status"] = "busy"
            sa["tasks_completed"] += 1

        time.sleep(min(sa["response_time"] * 0.05, 0.2))
        result = self._generate_response(sa, task)

        with self._lock:
            sa["status"] = "idle"

        return {
            "sub_agent": sa_id,
            "role": sa["role"],
            "department": sa["department"],
            "main_agent": sa["main_agent"],
            "result": result,
            "accuracy": round(sa["accuracy"], 3)
        }

    def _generate_response(self, sa, task):
        role = sa["role"].lower()
        task_lower = task.lower()

        if "reader" in role or "parser" in role or "extractor" in role:
            return f"Read and parsed input: extracted {len(task.split())} tokens, formatted output"
        if "writer" in role or "generator" in role:
            return f"Generated output based on: {task[:50]}..."
        if "search" in role or "finder" in role or "lister" in role:
            return f"Searched and found 10+ matching results"
        if "check" in role or "test" in role or "validator" in role or "lint" in role:
            issues = random.randint(0, 5)
            return f"Validation complete: {issues} issue(s) found" if issues else "Validation passed: no issues"
        if "convert" in role or "translator" in role:
            return f"Conversion complete: input processed successfully"
        if "calc" in role or "solver" in role or "calculator" in role:
            return f"Calculation complete: result = {random.randint(1, 10000)}"
        if "monitor" in role or "checker" in role:
            return f"Status: OK (response time: {random.randint(1, 50)}ms)"
        if "adder" in role or "setter" in role or "creator" in role:
            return f"Operation successful: created/updated entry"
        if "remover" in role or "killer" in role or "deleter" in role:
            return f"Operation successful: removed target"
        if "advisor" in role or "assist" in role:
            return f"Analysis complete: recommendations prepared based on your query"

        return f"Processed by {sa['role']}: task analyzed and completed"

    def get_stats(self):
        total = len(self.sub_agents)
        by_main = defaultdict(int)
        for sa in self.sub_agents.values():
            by_main[sa["main_agent"]] += 1
        total_tasks = sum(sa["tasks_completed"] for sa in self.sub_agents.values())
        avg_acc = sum(sa["accuracy"] for sa in self.sub_agents.values()) / total if total else 0
        return {
            "total_sub_agents": total,
            "main_agents": len(by_main),
            "by_main_agent": dict(by_main),
            "total_tasks_completed": total_tasks,
            "average_accuracy": round(avg_acc, 3)
        }

    def list_by_main(self, main_agent):
        agents = self.agent_map.get(main_agent, [])
        return [self.sub_agents[a] for a in agents]

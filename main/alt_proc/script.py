import os
import re
import sys
import traceback
import json

from alt_proc.dict_ import dict_
import alt_proc.time
import alt_proc.pg
import alt_proc.cfg
import alt_proc.os_

try:
    __IPYTHON__
    _debug = True
except:
    _debug = False


class Script:

    def __new__(cls):

        if not hasattr(cls, 'instance'):
            cls.instance = super(Script, cls).__new__(cls)
        return cls.instance

    def __init__(self):

        if not (hasattr(self, 'obj_id') and self.obj_id == id(self)):
            # print('Script init', self)
            self.obj_id = id(self)
            alt_proc_cfg = alt_proc.cfg.read_global('alt_proc')
            self.db = alt_proc.pg.DB(**alt_proc_cfg.db)

            self.mode = 'STANDALONE'

    def except_handler(self, exctype, err, tb):

        sys.excepthook = sys.__excepthook__
        traceback.print_exception(exctype, err, tb)
        tb = '\n'.join(traceback.format_tb(tb))
        self.fatal('Exception')

    def start(self):

        wd = os.getcwd()
        if 'procs' not in wd:
            print('alt_proc: standalone mode')
            return

        self.mode = 'DB'
        m = re.match('.+/procs/(\d*)/_(\d\d)_.+', wd)
        if not m:
            raise Exception('Wrong start dir')
        self.proc_id, self.iscript = [int(v) for v in m.groups()]
        self.alt_proc_wd = os.path.abspath(wd + '/../../../') + '/'
        self.errors = False
        self.debug = _debug
        self.msgs = []

        sql = """
            select e.params, t.project, s.script_id, t.status, s.script 
            from events e 
            left join procs p on e.event_id = p.event_id
            left join tasks t on t.task_id = e.task_id
            left join scripts s on p.proc_id = s.proc_id
            where p.proc_id=%s and iscript=%s
        """
        row = self.db.sql(sql, (self.proc_id, self.iscript), return_one=True)
        if self.debug and row.status != 'DEBUG':
            raise Exception('Not DEBUG mode')
        self.params = row.get('params', dict_())
        self.project, self.script_id, self.script_path = row.project, row.script_id, row.script

        print(alt_proc.time.now(), 'Script ', self.project, ':', self.script_path, 'started')

        sys.excepthook = self.except_handler

    def exit(self, fatal=False, restart_after=None):

        if self.mode == 'STANDALONE':
            sys.exit()

        result = 'SUCCESS'
        if self.errors:
            result = 'ERRORS'
        if fatal:
            result = 'FATAL'

        sql = """
            update scripts set status='DONE', result = %s, etime=now()
            where script_id=%s
            """
        self.db.sql(sql, (result, self.script_id))

        print(alt_proc.time.now(), 'Script finished')

        sys.exit()

    def emit_event(self, task, title, **params):

        print('Emit Event', task, title, params)

        if params:
            params = json.dumps(params)
        else:
            params = None

        sql = """
            select task_id from tasks where name=%s and status!='DELETED'
            """
        task = self.db.sql(sql, task, return_one=True)
        if not task:
            self.fatal('Unknown task name')

        sql = """
            insert into events (task_id, title, params) values (%s,%s,%s)
            """
        event_id = self.db.sql(sql, (task.task_id, title, params), return_id='event_id')

        return event_id

    def msg(self, msg_type, msg_str, data=None):

        print(msg_type, msg_str, data)

        if self.mode == 'DB':
            msg = dict_(type=msg_type, msg=str(msg_str))
            if data:
                msg.data = data
            self.msgs.append(msg)
            print(msg)

    def fatal(self, msg, restart_after=None, **kwds):

        self.msg('FATAL', msg, kwds)

        self.exit(fatal=True, restart_after=restart_after)

    def error(self, msg, **kwds):

        self.msg('ERROR', msg, kwds)

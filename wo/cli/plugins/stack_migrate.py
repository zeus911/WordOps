from cement.core.controller import CementBaseController, expose

from wo.cli.plugins.stack_pref import post_pref, pre_pref
from wo.core.aptget import WOAptGet
from wo.core.fileutils import WOFileUtils
from wo.core.logging import Log
from wo.core.mysql import WOMysql
from wo.core.shellexec import WOShellExec
from wo.core.variables import WOVar


class WOStackMigrateController(CementBaseController):
    class Meta:
        label = 'migrate'
        stacked_on = 'stack'
        stacked_type = 'nested'
        description = ('Migrate stack safely')
        arguments = [
            (['--mariadb'],
                dict(help="Migrate/Upgrade database to MariaDB",
                     action='store_true')),
            (['--force'],
                dict(help="Force Packages upgrade without any prompt",
                     action='store_true')),
        ]

    @expose(hide=True)
    def migrate_mariadb(self):
        # Backup all database
        WOMysql.backupAll(self, fulldump=True)

        # Add MariaDB repo
        Log.info(self, "Adding repository for MariaDB, please wait...")
        pre_pref(self, WOVar.wo_mysql)

        # Install MariaDB

        Log.info(self, "Updating apt-cache, hang on...")
        WOAptGet.update(self)
        Log.info(self, "Installing MariaDB, hang on...")
        WOAptGet.remove(self, ["mariadb-server"])
        WOAptGet.auto_remove(self)
        WOAptGet.install(self, WOVar.wo_mysql)
        post_pref(self, WOVar.wo_mysql, [])
        WOShellExec.cmd_exec(self, 'systemctl daemon-reload')
        WOFileUtils.mvfile(
            self, '/etc/mysql/my.cnf', '/etc/mysql/my.cnf.old')
        WOFileUtils.create_symlink(
            self, ['/etc/mysql/mariadb.cnf', '/etc/mysql/my.cnf'])

    @expose(hide=True)
    def default(self):
        pargs = self.app.pargs
        if ((not pargs.mariadb)):
            self.app.args.print_help()
        if pargs.mariadb:
            if WOVar.wo_mysql_host != "localhost":
                Log.error(
                    self, "Remote MySQL server in use, skipping local install")

            if (WOShellExec.cmd_exec(self, "mysqladmin ping")):

                Log.info(self, "If your database size is big, "
                         "migration may take some time.")
                Log.info(self, "During migration non nginx-cached parts of "
                         "your site may remain down")
                if not pargs.force:
                    start_upgrade = input("Do you want to continue:[y/N]")
                    if start_upgrade != "Y" and start_upgrade != "y":
                        Log.error(self, "Not starting package update")
                self.migrate_mariadb()
            else:
                Log.error(self, "Your current MySQL is not alive or "
                          "you allready installed MariaDB")

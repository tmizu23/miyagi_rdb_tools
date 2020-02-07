# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MiyagiRDBTools
                                 A QGIS plugin
 This plugin is tools for Miyagi RDB

        copyright            : (C) 2020 by Ecoris Inc.
        email                : mizutani@ecoris.co.jp
 ***************************************************************************/

"""
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .miyagi_rdb_tools_dialog import MiyagiRDBToolsDialog
import os.path
import datetime
from itertools import groupby
from operator import itemgetter

class MiyagiRDBTools:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MiyagiRDBTools_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Miyagi RDB Tools')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('MiyagiRDBTools', message)


    def add_action(self,icon_path,text,callback,enabled_flag=True,add_to_menu=True,add_to_toolbar=True,status_tip=None,whats_this=None,parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/miyagi_rdb_tools/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Miyagi RDB Tools'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Miyagi RDB Tools'),
                action)
            self.iface.removeToolBarIcon(action)

    def filter(self, features, field_name,rank="all", year_s="all", year_e="all"):
       """ filter by rank and not empty """
       class_idx = field_name.index("class")
       rank_idx = field_name.index("rank")
       year_idx = field_name.index("year")
       filterd = []
       for f in features:
           atrib = f.attributes()
           if atrib[class_idx]=="": #classがない。データなしは除く
               continue
           if rank!="all" and atrib[rank_idx] != rank: #rankがことなる
               continue
           if year_s!="all" and int(atrib[year_idx]) < int(year_s): #year_sが範囲外
               continue
           if year_e != "all" and int(atrib[year_idx]) > int(year_e): #year_eが範囲外
               continue
           filterd.append(f)

       return filterd

    def distinct(self, features, field_name, distinct_field):
        distinct_idx = [field_name.index(col) for col in distinct_field]
        features = sorted(features, key=lambda x: x[distinct_idx[0]])
        distinct_list = self.distinct_(features, distinct_idx, 0, distinct_list=[])
        return distinct_list, distinct_field

    def distinct_(self, features, distinct_idx, n, distinct_list=[]):
        for (k, g) in groupby(features, key=itemgetter(distinct_idx[n])):
            if len(distinct_idx) - 1 > n:
                g = sorted(g, key=lambda x: x[distinct_idx[n + 1]])
                distinct_list = self.distinct_(g, distinct_idx, n + 1, distinct_list)
            else:
                grouplist = list(g)
                selectattr = [grouplist[0][i] for i in distinct_idx]
                distinct_list.append(selectattr)
        return distinct_list

    def group_by_summarize(self, features, field_name, group_field, count_name=None):
        group_idx = [field_name.index(gf) for gf in group_field]
        if count_name != None:
            group_field.append(count_name)
        features = sorted(features, key=lambda x: x[group_idx[0]])
        group_by_list = self.group_by_(features, group_idx, count_name, 0, group_by_list=[])
        return group_by_list, group_field

    def group_by_(self, features, group_idx, count_name, n, group_by_list=[]):
        for (k, g) in groupby(features, key=itemgetter(group_idx[n])):
            if len(group_idx) - 1 > n:
                g = sorted(g, key=lambda x: x[group_idx[n + 1]])
                group_by_list = self.group_by_(g, group_idx, count_name, n + 1, group_by_list)
            else:
                grouplist = list(g)
                selectattr = [grouplist[0][i] for i in group_idx]
                if count_name != None:
                   selectattr.append(len(grouplist))
                group_by_list.append(selectattr)
        return group_by_list



    def writelist(self,features,field_name,f_path):
        csv_str = ",".join(field_name) + "\n"
        for f in features:
            csv_str = csv_str + ",".join(map(str, f)) + "\n"
        output_file = open(f_path, 'w', encoding='shift-jis')
        output_file.write(csv_str)
        output_file.close()
        return csv_str

    def selectFeatureByCode(self,layer,code_list):
        layer.removeSelection()
        for code in code_list:
            exp_str = '"code"=' + code
            layer.selectByExpression(exp_str, 1)
        return layer.selectedFeatures()

    def selectedCode(self,features,code_idx):
        code_list = [f.attributes()[code_idx] for f in features]
        distinct_code = list(set(code_list))
        return distinct_code

    def convertCode(self,code_list):
        if len(code_list[0])==6:
            code3R = []
            #2次メッシュを3次メッシュに
            for code in code_list:
                for x in range(10):
                  for y in range(10):
                     code3R.append(code + str(y) + str(x))
            return code3R
        else:
            #3次メッシュを2次メッシュに
            code2R = list(set([code[0:6] for code in code_list ]))
            return code2R

    def writeRDBInfo(self,outdir, layer, code_list, meshtype):
        try:
            """
          ToDo:
          field名を合わせて処理
          filterをexpressionで
          """
            isARankName = self.dlg.checkBox_Arank.checkState()
            year_s = self.dlg.dateEdit_start.dateTime().toString("yyyy")
            year_e = self.dlg.dateEdit_end.dateTime().toString("yyyy")

            field_name = ["fid", "code", "class", "name", "category", "rank", "year", "mesh2R", "mesh3R"]
            field_name_jp = ["fid", "メッシュ", "分類", "種名", "カテゴリ", "秘匿ランク", "確認年", "二次メシュ", "三次メッシュ"]

            features = self.selectFeatureByCode(layer, code_list)

            ### rank A
            rankA = self.filter(features, field_name, rank="A", year_s=year_s, year_e=year_e)
            distinct_field = ["メッシュ", "分類", "種名", "カテゴリ"]
            rankA_distinct, rankA_field = self.distinct(rankA, field_name_jp, distinct_field)
            if isARankName:
                f_path = outdir + "/" + "Aランク希少種_" + meshtype + ".csv"
                outstr = self.writelist(rankA_distinct, rankA_field, f_path)
            else:
                group_field = ["メッシュ", "分類", "カテゴリ"]
                rankA_summary, rankA_field = self.group_by_summarize(rankA_distinct, rankA_field, group_field,
                                                                     count_name="種数")
                f_path = outdir + "/" + "Aランク希少種_" + meshtype + ".csv"
                outstr = self.writelist(rankA_summary, rankA_field, f_path)
            QMessageBox.information(None, "Aランク希少種", outstr)

            ### rank B
            rankB = self.filter(features, field_name, rank="B", year_s=year_s, year_e=year_e)
            distinct_field = ["メッシュ", "分類", "種名", "カテゴリ"]
            rankB_summary, rankB_field = self.distinct(rankB, field_name_jp, distinct_field)
            f_path = outdir + "/" + "Bランク希少種_" + meshtype + ".csv"
            outstr = self.writelist(rankB_summary, rankB_field, f_path)
            QMessageBox.information(None, "選択範囲内のBランク希少種", outstr)

        except Exception as e:
            QMessageBox.warning(None, "注意", str(e.args))
            QMessageBox.warning(None, "注意", "レイヤとメッシュを正しく選択してください")

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
           self.first_start = False
           self.dlg = MiyagiRDBToolsDialog()
        self.dlg.button_box.button(QDialogButtonBox.Ok).setText("実行")
        self.dlg.checkBox_Arank.setCheckState(False)
        self.dlg.dateEdit_start.setDateTime(QDateTime.fromString("1900","yyyy"))
        self.dlg.dateEdit_end.setDateTime(QDateTime.fromString("2100","yyyy"))
        # show the dialog
        self.dlg.show()
        #Run the dialog event loop
        result = self.dlg.exec_()
        #See if OK was pressed
        if result:
            now = datetime.datetime.now().strftime('%Y%m%d%H%M')
            outdir = QFileInfo(QgsProject.instance().fileName()).dir().absolutePath() + "/情報提供" + now
            if not os.path.exists(outdir):
                os.mkdir(outdir)

            layer = self.iface.activeLayer()
            # クリックで選択すると一番上のメッシュしか選択されないため、コード番号で再選択
            code_idx = 1 ## ToDo:ハードコードを解消
            code_list = self.selectedCode(layer.selectedFeatures(), code_idx)

            layername = layer.name()
            if layername=="開発事業者向け（二次メッシュ）":
                self.writeRDBInfo(outdir,layer,code_list,"二次メッシュ")
            elif layername=="希少種保全施策者向け（三次メッシュ）":
                self.writeRDBInfo(outdir,layer,code_list,"三次メッシュ")
                ## 二次メッシュも書き出す
                code_list = self.convertCode(code_list)
                layers = QgsProject.instance().mapLayersByName('開発事業者向け（二次メッシュ）')
                layer = layers[0]
                self.writeRDBInfo(outdir,layer,code_list, "二次メッシュ")
            QMessageBox.information(None, "希少種情報", outdir + "に書き出しました。")


    def log(self, msg):
        QgsMessageLog.logMessage("{}".format(msg), 'MyPlugin', Qgis.Info)
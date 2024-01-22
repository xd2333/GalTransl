from GalTransl.yapsy.IPlugin import IPlugin
from GalTransl.CSentense import CSentense


class BasePlugin(IPlugin):

    def __init__(self):
        """
        Make some initializations if necessary.
        """
        super().__init__()
        pass

    def before_src_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called before the source sentence is processed.
        :param tran: The CSentense to be processed.
        :return: The modified CSentense."""
        return tran

    def after_src_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called after the source sentence is processed.
        :param tran: The CSentense to be processed.
        :return: The modified CSentense.
        """
        return tran

    def before_dst_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called before the destination sentence is processed.
        :param tran: The CSentense to be processed.
        :return: The modified CSentense.
        """
        return tran

    def after_dst_processed(self, tran: CSentense) -> CSentense:
        """
        This method is called after the destination sentence is processed.
        :param tran: The CSentense to be processed.
        :return: The modified CSentense.
        """
        return tran
    
    def after_all_transl_done(self):
        """
        This method is called after all translations are done.
        """
        pass

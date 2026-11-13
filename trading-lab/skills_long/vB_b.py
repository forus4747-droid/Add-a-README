from skills_long.vB_core import predict_cfg
def predict(panel, market): return predict_cfg(panel, market, dict(model='ridge', window=6, regime=False))

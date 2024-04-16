from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from sentiments import estimate_sentiment
from creds import BASE_URL, KEY_ID, SECRET_KEY, APLACA_CREDS

class Trader(Strategy):
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, 
                        key_id=KEY_ID, 
                        secret_key=SECRET_KEY)

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'),  three_days_prior.strftime('%Y-%m-%d')

    def position_meta(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_probability_and_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news ]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_meta()
        probability, sentiment = self.get_probability_and_sentiment()

        if cash > last_price:
            if probability > .999 and sentiment == "positive":
                if self.last_trade == "sell": 
                    self.make_trade(self, "buy", "bracket", last_price*1.20, last_price*.95, quantity)
            if probability > .999 and sentiment == "negative":
                if self.last_trade == "buy": 
                    self.make_trade(self, "sell", "bracket", last_price*.8, last_price*1.05, quantity)
        
    
    def make_trade(self, action:str, type:str, take_profit_price:float, stop_loss_price:float, quantity):
        order = self.create_order( 
                        self.symbol,
                        quantity,
                        action,
                        type=type,
                        take_profit_price=take_profit_price,
                        stop_loss_price=stop_loss_price
                    )
        self.submit_order(order)
        self.last_trade = action


broker = Alpaca(APLACA_CREDS)
strategy = Trader(name='mlstrat', 
                    broker= broker, 
                    parameters= {"symbol":"SPY", "cash_at_risk":.5})
start_date = datetime(2020,1,11)
end_date = datetime(2023,12,30)

strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters = {"symbol":"SPY", "cash_at_risk":.5}
)



from typing import Any, Dict, List, Optional
import akshare as ak
from dataclasses import dataclass, field
import logging
import traceback
import datetime
import math
import requests
from bs4 import BeautifulSoup
from django.core.cache import cache

logger = logging.getLogger("root")


@dataclass
class Fund(object):
    code: str
    name: Optional[str] = ""
    type: Optional[str] = ""
    fee: float = 0
    manager: Optional[str] = ""
    company: Optional[str] = ""
    scale: float = 0
    recommand: List[Any] = field(default_factory=list)

    stock: List[Dict[str, Any]] = field(default_factory=list)
    _stock_share: float = 0
    _bond_share: float = 0
    bond: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def star(self):
        avg = 0
        for v in self.recommand:
            avg += v["star"]
        if len(self.recommand) > 0:
            avg = avg / len(self.recommand)
        else:
            avg = 0
        return avg

    @property
    def stock_share(self) -> float:
        if self._stock_share != 0:
            return self._stock_share
        return self.head_stock_share

    @property
    def head_stock_share(self) -> float:
        v = 0
        for c in self.stock:
            v += c["share"]
        return v/100

    @property
    def bond_share(self) -> float:
        if self._bond_share != 0:
            return self._bond_share
        return self.head_bond_share

    @property
    def head_bond_share(self) -> float:
        v = 0
        for c in self.bond:
            v += c["share"]
        return v/100

    @property
    def other_share(self) -> float:
        return 1 - self.bond_share - self.stock_share

    @property
    def show_stock_share(self):
        return f"{self.stock_share*100:.2f}"

    @property
    def show_bond_share(self):
        return f"{self.bond_share*100:.2f}"

    @property
    def show_other_share(self):
        return f"{self.other_share*100:.2f}"

    @property
    def show_head_stock_share(self):
        return f"{self.head_stock_share*100:.2f}"

    @property
    def show_head_bond_share(self):
        return f"{self.head_bond_share*100:.2f}"

    @property
    def stock_season(self):
        try:
            return self.stock[0]["season"]
        except Exception:
            return None

    @property
    def bond_season(self):
        try:
            return self.bond[0]["season"]
        except Exception:
            return None


def get_fund(code: str):
    logger.info(f"getting fund info for {code}")
    try:
        fund = Fund(code)

        f = get_fund_info(code)
        logger.debug(f"getting basic information: {f}")
        if not f:
            return None
        fund.code = f['code']
        fund.name = f['name']
        fund.type = f['type']
        fund.fee = f['fee']

        f = get_fund_extra(code)
        logger.debug(f"getting extra information: {f}")

        if f:
            fund.manager = f['manager']
            fund.company = f['company']
            fund.recommand = f['recommend']

        f = get_fund_hold_stack(code)
        logger.debug(f"getting stock information: {f}")

        if f:
            fund.stock = f

        f = get_fund_hold_bond(code)
        logger.debug(f"getting bond information: {f}")

        if f:
            fund.bond = f

        f = get_fund_scale(code)
        logger.debug(f"getting bond information: {f}")
        if f:
            fund.scale = f["total_scale"]
            fund._stock_share = f["stock_share"]
            fund._bond_share = f["bond_share"]
    except Exception as e:
        traceback.print_exc()
        logger.error(f"get fund info error: {e}")
        return None
    return fund


def get_fund_info(code: str):
    fund_purchase_em_df = ak.fund_purchase_em()
    selected_fund = None

    selected_fund = fund_purchase_em_df[fund_purchase_em_df.基金代码 == code]
    try:
        selected_fund = selected_fund.iloc[0]
        return {
            "code": selected_fund['基金代码'],
            "name": selected_fund['基金简称'],
            "type": selected_fund['基金类型'],
            "fee": selected_fund['手续费'],
        }

    except Exception as e:
        traceback.print_exc()
        logger.error(f"get fund info error: {e}")
        return None


def get_fund_extra(code: str):
    fund_rating_all_df = ak.fund_rating_all()

    try:
        selected_fund = fund_rating_all_df[fund_rating_all_df.代码 == code]
        selected_fund = selected_fund.iloc[0]

        f = {
            "manager": selected_fund['基金经理'],
            "company": selected_fund['基金公司'],
            "recommend": []
        }

        for name in ["上海证券", "招商证券", "济安金信"]:
            value = selected_fund[name]
            if not value or math.isnan(value):
                continue
            f["recommend"].append({"name": name, "star": value})

    except Exception as e:
        logger.error(f"get fund info error: {e}")
        return None
    return f


def get_fund_hold_stack(code: str):
    today = datetime.date.today()

    try:
        year = today.year
        fund_portfolio_hold_em_df = ak.fund_portfolio_hold_em(symbol=code, date=f"{year}")
        if len(fund_portfolio_hold_em_df) == 0:
            fund_portfolio_hold_em_df = ak.fund_portfolio_hold_em(symbol=code, date=f"{year-1}")
        if len(fund_portfolio_hold_em_df) == 0:
            return None

        first_item = fund_portfolio_hold_em_df.iloc[0]

        season = first_item["季度"]
        fund_portfolio_hold_em_df = fund_portfolio_hold_em_df[fund_portfolio_hold_em_df.季度 == season]

        result = []
        for _, row in fund_portfolio_hold_em_df.iterrows():
            result.append({
                "code": row["股票代码"],
                "name": row["股票名称"],
                "share": row["占净值比例"],
                "season": season
            })
    except Exception as e:
        logger.error(f"get fund info error: {e}")
        return None
    return result


def get_fund_hold_bond(code: str):
    today = datetime.date.today()
    try:
        year = today.year
        fund_portfolio_bond_hold_em = ak.fund_portfolio_bond_hold_em(symbol=code, date=f"{year}")
        if len(fund_portfolio_bond_hold_em) == 0:
            fund_portfolio_bond_hold_em = ak.fund_portfolio_bond_hold_em(symbol=code, date=f"{year-1}")
        if len(fund_portfolio_bond_hold_em) == 0:
            return None

        first_item = fund_portfolio_bond_hold_em.iloc[0]

        season = first_item["季度"]
        fund_portfolio_bond_hold_em = fund_portfolio_bond_hold_em[fund_portfolio_bond_hold_em.季度 == season]

        result = []
        for _, row in fund_portfolio_bond_hold_em.iterrows():
            result.append({
                "code": row["债券代码"],
                "name": row["债券名称"],
                "share": row["占净值比例"],
                "season": season
            })
    except Exception as e:
        logger.error(f"get fund info error: {e}")
        return None
    return result


def get_fund_scale(code: str):
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.183"
    }

    try:
        resp = requests.get(f"https://fundf10.eastmoney.com/zcpz_{code}.html", headers=header)
        soup = BeautifulSoup(resp.text, 'html.parser')

        table = soup.find("table", attrs={"class": "w782 comm tzxq"})

        tbody = table.find("tbody")
        tr = tbody.find("tr")
        td_list = tr.find_all("td")
        logger.debug(td_list)
        try:
            stock_share = float(td_list[1].text.replace("%", "").replace("-", "")) / 100
        except Exception:
            stock_share = 0
        try:
            bond_share = float(td_list[2].text.replace("%", "").replace("-", "")) / 100
        except Exception:
            bond_share = 0

        other_share = 1 - stock_share - bond_share

        try:
            total_scale = float(td_list[-1].text)
        except Exception:
            total_scale = 0

        return {
            "stock_share": stock_share,
            "bond_share": bond_share,
            "other_share": other_share,
            "total_scale": total_scale
        }
    except Exception as e:
        logger.error(f"get fund scale error: {e}")
        return None


@dataclass
class FundPrice(object):
    code: str
    last_day: Optional[datetime.date] = None
    unit_price: Optional[float] = None
    cum_price: Optional[float] = None
    rate1: Optional[float] = None
    rate7: Optional[float] = None
    rate30: Optional[float] = None
    rate90: Optional[float] = None
    rate180: Optional[float] = None
    rate365: Optional[float] = None

    @property
    def show_rate_1(self):
        return f"{self.rate1*100:.2f}"

    @property
    def show_rate_7(self):
        return f"{self.rate7*100:.2f}"

    @property
    def show_rate_30(self):
        return f"{self.rate30*100:.2f}"

    @property
    def show_rate_90(self):
        return f"{self.rate90*100:.2f}"

    @property
    def show_rate_180(self):
        return f"{self.rate180*100:.2f}"

    @property
    def show_rate_365(self):
        return f"{self.rate365*100:.2f}"


def get_price(code: str) -> Optional[FundPrice]:
    result = FundPrice(code=code)
    try:
        fund_open_fund_info_em_df = ak.fund_open_fund_info_em(fund=code, indicator="单位净值走势")
        last_elem = fund_open_fund_info_em_df.iloc[-1]
        result.last_day = last_elem["净值日期"]
        result.unit_price = last_elem["单位净值"]
        result.rate1 = last_elem["日增长率"] / 100

        dd = ak.fund_open_fund_info_em(fund=code, indicator="累计净值走势")
        last_elem = dd.iloc[-1]
        result.cum_price = last_elem["累计净值"]

        for diff_day in [7, 30, 90, 180, 365]:
            try:
                start_day = result.last_day - datetime.timedelta(days=diff_day)
                price = fund_open_fund_info_em_df[fund_open_fund_info_em_df.净值日期 >= start_day]
                start_elem = price.iloc[0]
                start_price = start_elem["单位净值"]
                setattr(result, f"rate{diff_day}", result.unit_price/start_price - 1)
            except Exception as e:
                logger.error(f"get price diff_day {diff_day} error: {e}")
                pass
    except Exception as e:
        logger.error(f"get price error: {e}")
        return None
    logger.info(f"successfully update price for {code}")
    return result


def get_rt_factor():
    rt_price_timeout = 300
    now = cache.get("rt_now", default=None)
    if now is None:
        try:
            now = datetime.datetime.now()
            cache.set("rt_now", now, rt_price_timeout)
        except Exception as e:
            logger.error(f"get rt now error: {e}")
            now = None
    rt_factor_cache_timeout = rt_price_timeout
    a_stocks = cache.get("rt_a_stocks", default=None)
    if a_stocks is None:
        try:
            a_stocks_tmp = ak.stock_zh_a_spot_em()
            a_stocks = {}
            for _, row in a_stocks_tmp.iterrows():
                a_stocks[row["代码"]] = row["涨跌幅"] / 100
        except Exception as e:
            logger.error(f"get rt a stocks error: {e}")
            a_stocks = None
        if a_stocks:
            logger.info(a_stocks)
            cache.set("rt_a_stocks", a_stocks, rt_factor_cache_timeout)
            logger.info(a_stocks)

    h_stocks = cache.get("rt_h_stocks", default=None)
    if h_stocks is None:
        try:
            h_stocks_tmp = ak.stock_hk_spot_em()
            h_stocks = {}
            for _, row in h_stocks_tmp.iterrows():
                h_stocks[row["代码"]] = row["涨跌幅"] / 100
        except Exception as e:
            logger.error(f"get rt h stocks error: {e}")
            h_stocks = None
        if h_stocks:
            cache.set("rt_h_stocks", h_stocks, rt_factor_cache_timeout)

    m_stocks = cache.get("rt_m_stocks", default=None)
    if m_stocks is None:
        try:
            m_stocks_tmp = ak.stock_us_spot_em()
            m_stocks = {}
            for _, row in m_stocks_tmp.iterrows():
                code = row["代码"]
                if "." in code:
                    code = code.split(".")[1]
                m_stocks[code] = row["涨跌幅"] / 100
        except Exception as e:
            logger.error(f"get rt m stocks error: {e}")
            m_stocks = None
        if m_stocks:
            cache.set("rt_m_stocks", m_stocks, rt_factor_cache_timeout)

    bond_index = cache.get("rt_bond_index", default=None)
    if bond_index is None:
        try:
            bond_index = {}
            bond__normal_index = ak.bond_new_composite_index_cbond(indicator="财富", period="总值")
            start_price = bond__normal_index.iloc[-2]["value"]
            end_price = bond__normal_index.iloc[-1]["value"]
            bond_rate = end_price/start_price-1
            bond_index["bond"] = bond_rate
            bond_cb_index = ak.bond_cb_index_jsl()
            bond_cb_rate = bond_cb_index.iloc[-1]["increase_val"] / 100
            bond_index["bond_cb"] = bond_cb_rate
        except Exception as e:
            logger.error(f"get rt bond index error: {e}")
            bond_index = None
        if bond_index:
            cache.set("rt_bond_index", bond_index, rt_factor_cache_timeout)

    return now, a_stocks, h_stocks, m_stocks, bond_index


def get_rt_price(fund: Fund) -> Optional[float]:
    now, a_stocks, h_stocks, m_stocks, bond_index = get_rt_factor()
    logger.info(f"getting rt price for {fund.code} time {now}")
    stock_share_all = fund.stock_share
    bond_share_all = fund.bond_share

    stock_share_account = 0
    stock_price_total = 0
    for stock in fund.stock:
        try:
            stock_code = stock['code']
            stock_share = stock['share']

            if stock_code in a_stocks:
                stock_price = a_stocks[stock_code]
            elif stock_code in h_stocks:
                stock_price = h_stocks[stock_code]
            elif stock_code in m_stocks:
                stock_price = m_stocks[stock_code]
            else:
                continue
            logger.debug(f"update stock rate: {stock_code} {stock_price} {stock_share}")
            stock_share_account += stock_share
            stock_price_total += stock_share * stock_price
        except Exception:
            traceback.print_exc()
            continue
    logger.debug(stock_share_account)
    stock_evaluate_rate = stock_price_total / stock_share_account if stock_share_account > 0 else 0
    logger.debug(f"update avg stock rate: {stock_evaluate_rate}")

    try:
        bond_rate = bond_index["bond"]
        logger.debug(f"update avg bond rate: {bond_rate}")
        bond_cb_rate = bond_index["bond_cb"]
        logger.debug(f"update avg bond cb rate: {bond_cb_rate}")
    except Exception as e:
        logger.error(f"update avg bond error: {e}")
        bond_rate = 0
        bond_cb_rate = 0

    bond_share_total = 0
    bond_cb_share_total = 0
    for b in fund.bond:
        try:
            name = b["name"]
            share = b["share"]

            if "转" in name:
                bond_cb_share_total += share
            else:
                bond_share_total += share
        except Exception:
            continue

    bond_evaluate_rate = (bond_cb_rate * bond_cb_share_total + bond_rate * bond_share_total)/(bond_cb_share_total+bond_share_total) if bond_cb_share_total+bond_share_total > 0 else 0

    logger.debug(f"update avg stock rate: {bond_evaluate_rate} bond_share: {bond_share_total} bond_rate: {bond_rate} bond_cb_share: {bond_cb_share_total} bond_cb_rate: {bond_cb_rate}")

    evaluate_rate = stock_share_all * stock_evaluate_rate + bond_evaluate_rate * bond_share_all
    logger.debug(f"update evaluated: {evaluate_rate} {stock_evaluate_rate}({stock_share_all}) {bond_evaluate_rate}({bond_share_all})")
    return now, evaluate_rate


def get_index():
    index_cache_timeout = 300
    now = cache.get("index_now", default=None)
    if now is None:
        try:
            now = datetime.datetime.now()
            cache.set("index_now", now, index_cache_timeout)
        except Exception as e:
            logger.error(f"get index now error: {e}")
            now = None
    china_index = cache.get("china_index", default=None)
    if china_index is None:
        tmp_index = []
        stock_zh_index_spot_df = ak.stock_zh_index_spot()
        for code in ["sh000001", "sh000300", "sh000016", "sz399006"]:
            row = stock_zh_index_spot_df[stock_zh_index_spot_df["代码"] == code].iloc[0]
            tmp_index.append({
                "name": row["名称"],
                "code": row["代码"],
                "price": row["最新价"],
                "rate": row["涨跌幅"],
            })
            logger.debug(row)
        if len(tmp_index) > 0:
            china_index = tmp_index
            cache.set("china_index", china_index, index_cache_timeout)
    return now, china_index


if __name__ == "__main__":
    # fund = get_fund("000001")
    # print(fund.star)
    # print(fund.stock_share)
    # print(fund.bond_share)
    # print(fund.other_share)
    # print(fund.scale)
    bond__normal_index = ak.bond_new_composite_index_cbond(indicator="财富", period="总值")
    print(bond__normal_index)
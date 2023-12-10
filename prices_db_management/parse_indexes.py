import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

from parse_base import ParseBase
from fetch_common import Asset

class ParseIndices(ParseBase):
    def main(self):
        # I only need DAX because others I'm interested in are captured in some widely-traded ETF.
        assets = [Asset(ticker='^GDAXI', name='DAX PERFORMANCE-INDEX')]
        self.fetch_and_store_pricing_history(asset_type='INDEX', assets=assets)

if __name__ == "__main__":
    ParseIndices().main()

-- ICAO to State Mapping Query for Australian Airports
-- Maps ICAO codes to states and finds pilots from 'Y' locations who flew last week
-- Top 200 results with complete state information

WITH icao_state_mapping AS (
    -- Major Australian Airports with ICAO codes and state mapping
    SELECT 'YSSY' as icao_code, 'New South Wales' as state, 'Sydney' as municipality UNION ALL
    SELECT 'YMML', 'Victoria', 'Melbourne' UNION ALL
    SELECT 'YBBN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YPPH', 'Western Australia', 'Perth' UNION ALL
    SELECT 'YBCS', 'Queensland', 'Cairns' UNION ALL
    SELECT 'YPAD', 'South Australia', 'Adelaide' UNION ALL
    SELECT 'YPDN', 'Northern Territory', 'Darwin' UNION ALL
    SELECT 'YBCG', 'Queensland', 'Gold Coast' UNION ALL
    SELECT 'YSCB', 'Australian Capital Territory', 'Canberra' UNION ALL
    SELECT 'YMHB', 'Tasmania', 'Hobart' UNION ALL
    SELECT 'YBAS', 'Northern Territory', 'Alice Springs' UNION ALL
    SELECT 'YMLT', 'Tasmania', 'Launceston' UNION ALL
    SELECT 'YBTL', 'Queensland', 'Townsville' UNION ALL
    SELECT 'YAYE', 'Northern Territory', 'Yulara' UNION ALL
    SELECT 'YBSU', 'Queensland', 'Maroochydore' UNION ALL
    SELECT 'YSBK', 'New South Wales', 'Sydney' UNION ALL
    SELECT 'YMAV', 'Victoria', 'Lara' UNION ALL
    SELECT 'YMMB', 'Victoria', 'Melbourne' UNION ALL
    SELECT 'YBHM', 'Queensland', 'Hamilton Island' UNION ALL
    SELECT 'YBRK', 'Queensland', 'Rockhampton' UNION ALL
    SELECT 'YPJT', 'Western Australia', 'Perth' UNION ALL
    SELECT 'YBAF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YMEN', 'Victoria', 'Essendon Fields' UNION ALL
    SELECT 'YBRM', 'Western Australia', 'Broome' UNION ALL
    SELECT 'YWLM', 'New South Wales', 'Williamtown' UNION ALL
    SELECT 'YPPF', 'South Australia', 'Adelaide' UNION ALL
    SELECT 'YCFS', 'New South Wales', 'Coffs Harbour' UNION ALL
    SELECT 'YMIA', 'Victoria', 'Mildura' UNION ALL
    SELECT 'YSCN', 'New South Wales', 'Cobbitty' UNION ALL
    SELECT 'YBNA', 'New South Wales', 'Ballina' UNION ALL
    SELECT 'YPKG', 'Western Australia', 'Broadwood' UNION ALL
    SELECT 'YBUD', 'Queensland', 'Bundaberg' UNION ALL
    SELECT 'YCNK', 'New South Wales', 'Cessnock' UNION ALL
    SELECT 'YKSC', 'South Australia', 'Kingscote' UNION ALL
    SELECT 'YSHL', 'New South Wales', 'Albion Park Rail' UNION ALL
    SELECT 'YBHI', 'New South Wales', 'Broken Hill' UNION ALL
    SELECT 'YSTW', 'New South Wales', 'Tamworth' UNION ALL
    SELECT 'YBUN', 'Western Australia', 'Bunbury' UNION ALL
    SELECT 'YSWG', 'New South Wales', 'Forest Hill' UNION ALL
    SELECT 'YBMK', 'Queensland', 'Mackay' UNION ALL
    SELECT 'YMER', 'New South Wales', 'Merimbula' UNION ALL
    SELECT 'YSHT', 'Victoria', 'Shepparton' UNION ALL
    SELECT 'YSWH', 'Victoria', 'Swan Hill' UNION ALL
    SELECT 'YRTI', 'Western Australia', 'Rottnest Island' UNION ALL
    SELECT 'YBDG', 'Victoria', 'Bendigo' UNION ALL
    SELECT 'YPAG', 'South Australia', 'Port Augusta' UNION ALL
    SELECT 'YABA', 'Western Australia', 'Albany' UNION ALL
    SELECT 'YBTH', 'New South Wales', 'Bathurst' UNION ALL
    SELECT 'YGEL', 'Western Australia', 'Moonyoonooka' UNION ALL
    SELECT 'YBMA', 'Queensland', 'Mount Isa' UNION ALL
    SELECT 'YECH', 'Victoria', 'Echuca' UNION ALL
    SELECT 'YMDG', 'New South Wales', 'Mudgee' UNION ALL
    SELECT 'YORG', 'New South Wales', 'Orange' UNION ALL
    SELECT 'YLHI', 'New South Wales', 'Lord Howe Island' UNION ALL
    SELECT 'YBSS', 'Victoria', 'Bacchus Marsh' UNION ALL
    SELECT 'YRED', 'Queensland', 'Redcliffe' UNION ALL
    SELECT 'YBDV', 'Queensland', 'Birdsville' UNION ALL
    SELECT 'YDPO', 'Tasmania', 'Devonport' UNION ALL
    SELECT 'YMAY', 'New South Wales', 'East Albury' UNION ALL
    SELECT 'YHBA', 'Queensland', 'Hervey Bay' UNION ALL
    SELECT 'YPKA', 'Western Australia', 'Karratha' UNION ALL
    SELECT 'YPKU', 'Western Australia', 'Kununurra' UNION ALL
    SELECT 'YBPN', 'Queensland', 'Proserpine' UNION ALL
    SELECT 'YPTN', 'Northern Territory', 'Tindal' UNION ALL
    SELECT 'YWGT', 'Victoria', 'Laceby' UNION ALL
    SELECT 'YLTV', 'Victoria', 'Morwell' UNION ALL
    SELECT 'YBLT', 'Victoria', 'Ballarat' UNION ALL
    SELECT 'YTDN', 'Victoria', 'Tooradin' UNION ALL
    SELECT 'YMUL', 'Western Australia', 'Murray Field' UNION ALL
    SELECT 'YMND', 'New South Wales', 'Maitland' UNION ALL
    SELECT 'YARM', 'New South Wales', 'Armidale' UNION ALL
    SELECT 'YWYY', 'Tasmania', 'Burnie' UNION ALL
    SELECT 'YCBP', 'South Australia', 'Coober Pedy' UNION ALL
    SELECT 'YLIS', 'New South Wales', 'Lismore' UNION ALL
    SELECT 'YPKS', 'New South Wales', 'Parkes' UNION ALL
    SELECT 'YPPD', 'Western Australia', 'Port Hedland' UNION ALL
    SELECT 'YROM', 'Queensland', 'Roma' UNION ALL
    SELECT 'YBWP', 'Queensland', 'Weipa' UNION ALL
    SELECT 'YWHA', 'South Australia', 'Whyalla' UNION ALL
    SELECT 'YCWR', 'New South Wales', 'Cowra' UNION ALL
    SELECT 'YGLB', 'New South Wales', 'Goulburn' UNION ALL
    SELECT 'YTEM', 'New South Wales', 'Temora' UNION ALL
    SELECT 'YNPE', 'Queensland', 'Bamaga' UNION ALL
    SELECT 'YPLM', 'Western Australia', 'Exmouth' UNION ALL
    SELECT 'YGLA', 'Queensland', 'Gladstone' UNION ALL
    SELECT 'YGTH', 'New South Wales', 'Griffith' UNION ALL
    SELECT 'YHID', 'Queensland', 'Horn' UNION ALL
    SELECT 'YPGV', 'Northern Territory', 'Nhulunbuy' UNION ALL
    SELECT 'YPBO', 'Western Australia', 'Paraburdoo' UNION ALL
    SELECT 'YPMQ', 'New South Wales', 'Port Macquarie' UNION ALL
    SELECT 'YAMB', 'Queensland', 'RAAF Base Amberley' UNION ALL
    SELECT 'YSRI', 'New South Wales', 'Richmond' UNION ALL
    SELECT 'YBLN', 'Western Australia', 'Busselton' UNION ALL
    SELECT 'YYWG', 'Victoria', 'Yarrawonga' UNION ALL
    SELECT 'YLIL', 'Victoria', 'Lilydale' UNION ALL
    SELECT 'YMGT', 'Western Australia', 'Margaret River' UNION ALL
    SELECT 'YCDR', 'Queensland', 'Caloundra' UNION ALL
    SELECT 'YCBG', 'Tasmania', 'Cambridge' UNION ALL
    SELECT 'YLEG', 'Victoria', 'Leongatha South' UNION ALL
    SELECT 'YSHL', 'New South Wales', 'Albion Park Rail' UNION ALL
    SELECT 'YBRM', 'Western Australia', 'Broome' UNION ALL
    SELECT 'YBRK', 'Queensland', 'Rockhampton' UNION ALL
    SELECT 'YBRN', 'Queensland', 'Bundaberg' UNION ALL
    SELECT 'YBRS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBRZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSS', 'Victoria', 'Bacchus Marsh' UNION ALL
    SELECT 'YBST', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSU', 'Queensland', 'Maroochydore' UNION ALL
    SELECT 'YBSV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBSZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTH', 'New South Wales', 'Bathurst' UNION ALL
    SELECT 'YBTI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTL', 'Queensland', 'Townsville' UNION ALL
    SELECT 'YBTM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBTZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUD', 'Queensland', 'Bundaberg' UNION ALL
    SELECT 'YBUE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBUZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBVZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWP', 'Queensland', 'Weipa' UNION ALL
    SELECT 'YBWQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBWZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBXZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBYZ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZA', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZB', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZC', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZD', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZE', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZF', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZG', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZH', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZI', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZJ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZK', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZL', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZM', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZN', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZO', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZP', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZQ', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZR', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZS', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZT', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZU', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZV', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZW', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZX', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZY', 'Queensland', 'Brisbane' UNION ALL
    SELECT 'YBZZ', 'Queensland', 'Brisbane'
),
pilot_origins AS (
    SELECT 
        f.callsign,
        f.cid,
        f.departure,
        RIGHT(f.departure, 4) as extracted_icao,
        m.state,
        m.municipality,
        f.completion_time,
        f.controller_time_percentage,
        ROW_NUMBER() OVER (ORDER BY f.completion_time DESC, f.callsign) as row_num
    FROM flight_summaries f
    LEFT JOIN icao_state_mapping m ON RIGHT(f.departure, 4) = m.icao_code
    WHERE f.departure IS NOT NULL 
        AND f.departure != ''
        AND f.departure LIKE 'Y%'
        AND f.completion_time >= CURRENT_DATE - INTERVAL '7 days'
        AND LENGTH(f.departure) >= 4
)
SELECT 
    callsign,
    cid,
    departure as origin_airport,
    extracted_icao,
    state,
    municipality,
    completion_time,
    controller_time_percentage
FROM pilot_origins
WHERE row_num <= 200
    AND state IS NOT NULL
ORDER BY completion_time DESC, callsign;

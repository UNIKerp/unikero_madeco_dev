select company_id, intrastat_transport_id, madeco_transport_id, count(*) from sale_order  where company_id = 1 group by 1,2,3 order by 1,2,3;
update sale_order set madeco_transport_id = 1 where company_id = 1 and intrastat_transport_id = 9;
update sale_order set madeco_transport_id = 2 where company_id = 1 and intrastat_transport_id = 12;
update sale_order set madeco_transport_id = 3 where company_id = 1 and intrastat_transport_id = 13;
update sale_order set madeco_transport_id = 4 where company_id = 1 and intrastat_transport_id = 14;
update sale_order set madeco_transport_id = 5 where company_id = 1 and intrastat_transport_id = 24;
update sale_order set madeco_transport_id = 6 where company_id = 1 and intrastat_transport_id = 15;
update sale_order set madeco_transport_id = 7 where company_id = 1 and intrastat_transport_id = 17;
update sale_order set madeco_transport_id = 8 where company_id = 1 and intrastat_transport_id = 18;
update sale_order set madeco_transport_id = 9 where company_id = 1 and intrastat_transport_id = 5;
update sale_order set madeco_transport_id = 10 where company_id = 1 and intrastat_transport_id = 19;

select company_id, intrastat_transport_id, madeco_transport_id, count(*) from stock_picking where company_id = 1 group by 1,2,3 order by 1,2,3;
update stock_picking set madeco_transport_id = 1 where company_id = 1 and intrastat_transport_id = 9;
update stock_picking set madeco_transport_id = 2 where company_id = 1 and intrastat_transport_id = 12;
update stock_picking set madeco_transport_id = 3 where company_id = 1 and intrastat_transport_id = 13;
update stock_picking set madeco_transport_id = 4 where company_id = 1 and intrastat_transport_id = 14;
update stock_picking set madeco_transport_id = 5 where company_id = 1 and intrastat_transport_id = 24;
update stock_picking set madeco_transport_id = 6 where company_id = 1 and intrastat_transport_id = 15;
update stock_picking set madeco_transport_id = 7 where company_id = 1 and intrastat_transport_id = 17;
update stock_picking set madeco_transport_id = 8 where company_id = 1 and intrastat_transport_id = 18;
update stock_picking set madeco_transport_id = 9 where company_id = 1 and intrastat_transport_id = 5;
update stock_picking set madeco_transport_id = 10 where company_id = 1 and intrastat_transport_id = 19;

select company_id, intrastat_transport_id, madeco_transport_id, count(*) from account_move where company_id = 1 group by 1,2,3 order by 1,2,3;
update account_move set madeco_transport_id = 1 where company_id = 1 and intrastat_transport_id = 9;
update account_move set madeco_transport_id = 2 where company_id = 1 and intrastat_transport_id = 12;
update account_move set madeco_transport_id = 3 where company_id = 1 and intrastat_transport_id = 13;
update account_move set madeco_transport_id = 4 where company_id = 1 and intrastat_transport_id = 14;
update account_move set madeco_transport_id = 5 where company_id = 1 and intrastat_transport_id = 24;
update account_move set madeco_transport_id = 6 where company_id = 1 and intrastat_transport_id = 15;
update account_move set madeco_transport_id = 7 where company_id = 1 and intrastat_transport_id = 17;
update account_move set madeco_transport_id = 8 where company_id = 1 and intrastat_transport_id = 18;
update account_move set madeco_transport_id = 9 where company_id = 1 and intrastat_transport_id = 5;
update account_move set madeco_transport_id = 10 where company_id = 1 and intrastat_transport_id = 19;
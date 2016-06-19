update product_product
set attributes = replace(attributes, '"available": false', '"active": true')
where id > 11



update product_product
set attributes = replace(attributes, '{"image_tn":', '{"available": true, "image_tn":')
where id > 11


select table_name from information_schema.columns where column_name = 'default_accounts_category';
-- default_cost_price_method
select * from ir_model_field where name = 'default_cost_price_method';

select * from ir_model_field where relation = 'account.account';


select * from ir_model_data where fs_values like '%product%';


select * from ir_property where id > 0;


select * from ir_model where model like '%term%'

select * from ir_property where res like '%account.configuration%'
select * from ir_property where value like '%account.account%'
28;1;"2016-05-03 08:33:10.08797";"";"account.account,2";;1996;"";1
29;1;"2016-05-03 08:33:10.08797";"";"account.account,2";;1962;"";1
31;1;"2016-05-03 08:33:10.08797";"";"account.account,4";;1998;"";1
32;1;"2016-05-03 08:33:10.08797";"";"account.account,4";;1971;"";1
34;1;"2016-05-03 08:33:10.08797";"";"account.account,5";;1675;"";1
35;1;"2016-05-03 08:33:10.08797";"";"account.account,13";;1674;"";1
36;1;"2016-05-03 08:33:59.349865";"account.configuration,1";"account.account,6";;2250;"";1
select * from ir_model_field where name = 'account_revenue';
select * from ir_model where ir_model.id > 70 and ir_model.id < 80;
71;"ir.rule.group-res.group";"Rule Group - Group";"Rule Group - Group";"res"
72;"ir.rule.group-res.user";"Rule Group - User";"Rule Group - User";"res"
73;"ir.sequence.type-res.group";"Sequence Type - Group";"Sequence Type - Group";"res"
74;"product.uom.category";"Product uom category";"Product uom category";"product"
75;"product.uom";"Unit of measure";"Unit of measure";"product"
76;"product.category";"Product Category";"Product Category";"product"
77;"product.template";"Product Template";"Product Template";"product"
78;"product.product";"Product Variant";"Product Variant";"product"
79;"product.template-product.category";"Template - Category";"Template - Category";"product"

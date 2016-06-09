update product_product
set attributes = replace(attributes, '"available": false', '"active": true')
where id > 11



update product_product
set attributes = replace(attributes, '{"image_tn":', '{"available": true, "image_tn":')
where id > 11



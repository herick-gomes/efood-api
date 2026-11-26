-- Efood | restore the original EBAC demo catalog (2026-11-26 snapshot).
-- Source: https://api-ebac.vercel.app/api/efood/restaurantes
-- Imports 6 restaurants and 22 products. DOES NOT alter existing rows, orders or stock.
-- Repeatable: only missing rows for efood_legacy_import will be inserted.
-- Recommended: export a Neon backup before running. Execute in SQL Editor on the intended branch.

BEGIN;

INSERT INTO shop_user (
    username, password, last_login, is_superuser, first_name, last_name,
    email, is_staff, is_active, date_joined, role
) VALUES (
    'efood_legacy_import', '!', NULL, FALSE, '', '', '', FALSE, TRUE, NOW(), 'merchant'
) ON CONFLICT (username) DO NOTHING;

WITH original_restaurants (name, category, description, image_url, featured) AS (
    VALUES
        ('Bella Tavola Italiana', 'italiana', 'A paixão dos nossos talentosos chefs pela cozinha italiana é evidente em cada prato, desde massas caseiras e risotos cremosos até suculentos frutos do mar e carnes tenras. Nosso menu é complementado por uma excelente carta de vinhos, cuidadosamente selecionados para harmonizar com a riqueza dos sabores italianos.', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//capa.jpeg', TRUE),
        ('Casa das Delícias Árabes', 'árabe', 'A Casa das Delícias Árabes é um acolhedor e autêntico restaurante árabe, localizado no coração da cidade, que proporciona uma verdadeira experiência culinária do Oriente Médio. O ambiente é decorado com elementos tradicionais e exóticos, criando uma atmosfera convidativa e confortável.', 'https://api-ebac.vercel.app/efood/casa_delicias_arabes//capa.jpeg', FALSE),
        ('Sakura Sushi House', 'japonês', 'A Sakura Sushi House é um sofisticado e autêntico restaurante japonês que oferece uma experiência culinária imersiva, transportando os visitantes diretamente para a Terra do Sol Nascente. O ambiente elegante é complementado por um belo jardim japonês, criando uma atmosfera tranquila e serena.', 'https://api-ebac.vercel.app/efood/sakura_sushi_house//capa.jpeg', FALSE),
        ('Cantinho Lusitano', 'português', 'O Cantinho Lusitano é um charmoso e tradicional restaurante português, que celebra a rica herança culinária de Portugal. Neste aconchegante espaço, os visitantes podem desfrutar dos autênticos sabores portugueses, preparados com ingredientes frescos e de alta qualidade, respeitando as receitas clássicas.', 'https://api-ebac.vercel.app/efood/cantinho_lusitano//capa.jpeg', FALSE),
        ('Piazza del Forno', 'pizzaria', 'A Piazza del Forno é uma pizzaria acolhedora e autêntica que se orgulha de suas raízes italianas. Aqui, você encontrará pizzas artesanais preparadas com ingredientes frescos e assadas em forno a lenha, proporcionando sabores inigualáveis e uma crosta crocante e deliciosa.', 'https://api-ebac.vercel.app/efood/piazza//capa.png', FALSE),
        ('Jardim da Terra', 'vegano', 'O Jardim da Terra é um restaurante vegano que se dedica a oferecer pratos deliciosos e criativos, utilizando apenas ingredientes frescos, orgânicos e sazonais. Nosso cardápio é cuidadosamente elaborado para proporcionar uma experiência culinária única, que celebra a diversidade e a riqueza dos alimentos à base de plantas.', 'https://api-ebac.vercel.app/efood/jardim_terra//capa.png', TRUE)
)
INSERT INTO shop_restaurant (
    owner_id, name, category, description, image_url,
    is_open, is_active, featured, created_at
)
SELECT
    u.id, data.name, data.category, data.description, data.image_url,
    TRUE, TRUE, data.featured, NOW()
FROM original_restaurants data
JOIN shop_user u ON u.username = 'efood_legacy_import' AND u.role = 'merchant'
WHERE NOT EXISTS (
    SELECT 1 FROM shop_restaurant r WHERE r.owner_id = u.id AND r.name = data.name
);

WITH original_products (restaurant_name, name, description, portion, image_url, price) AS (
    VALUES
        ('Bella Tavola Italiana', 'Ravioli al Tartufo Nero', 'O Ravioli al Tartufo Nero é um requintado prato de massa artesanal, que celebra os sabores ricos e terrosos da trufa negra italiana. Cada ravióli é cuidadosamente recheado com uma mistura saborosa de ricota fresca, parmesão e trufas negras raladas, proporcionando uma combinação de texturas suaves e aromas irresistíveis.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//1.webp', 69.90),
        ('Bella Tavola Italiana', 'Spaghetti alla Carbonara', 'O Spaghetti alla Carbonara é um clássico prato italiano, feito com massa spaghetti al dente, coberto com um molho rico e cremoso à base de ovos, queijo pecorino romano, pancetta e pimenta-do-reino. Um prato saboroso e reconfortante que leva você diretamente para a Itália.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//2.jpg', 56.90),
        ('Bella Tavola Italiana', 'Risotto ai Funghi Porcini', 'O Risotto ai Funghi Porcini é uma iguaria italiana feita com arroz Arborio de alta qualidade e cogumelos porcini secos, que são reidratados para liberar seu sabor intenso e terroso. O arroz é cozido lentamente em um caldo de legumes, com vinho branco e queijo parmesão, resultando em um risoto cremoso e delicioso.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//3.jpg', 74.90),
        ('Bella Tavola Italiana', 'Ossobuco alla Milanese', 'O Ossobuco alla Milanese é um tradicional prato italiano, originário de Milão, que consiste em um suculento pedaço de vitela cozido lentamente em um molho à base de tomate, vinho branco e legumes. O prato é acompanhado por uma porção de polenta cremosa ou risoto alla Milanese, feito com açafrão.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//4.jpg', 89.90),
        ('Bella Tavola Italiana', 'Melanzane alla Parmigiana', 'Melanzane alla Parmigiana é um delicioso prato à base de berinjelas, em camadas com molho de tomate caseiro, queijo muçarela e parmesão, assado até ficar dourado e borbulhante. Uma opção saborosa e reconfortante, perfeita para os amantes de legumes e queijo.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//5.jpg', 62.90),
        ('Bella Tavola Italiana', 'Frutti di Mare Linguine', 'O Frutti di Mare Linguine é uma verdadeira celebração dos sabores do mar, apresentando uma generosa mistura de frutos do mar frescos, como camarões, lulas, mariscos e vieiras, combinados com massa linguine al dente e um saboroso molho de tomate e vinho branco. Uma opção deliciosa para os amantes de frutos do mar.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//6.jpg', 84.90),
        ('Bella Tavola Italiana', 'Insalata Caprese', 'A Insalata Caprese é uma refrescante e deliciosa salada italiana, feita com tomates maduros e suculentos, fatias frescas de mozzarella di bufala, folhas de manjericão e um fio de azeite extra virgem de oliva. Uma opção leve e saborosa, perfeita como entrada ou acompanhamento.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/bella_tavola_italiana//7.jpg', 49.90),
        ('Casa das Delícias Árabes', 'Mezze Platter', 'O Mezze Platter é uma seleção de aperitivos tradicionais árabes, incluindo homus, babaganush, tabule, falafel, azeitonas e pão pita fresco. Uma combinação deliciosa de sabores e texturas que proporciona uma experiência gastronômica única e diversificada.', '2 a 4 pessoas', 'https://api-ebac.vercel.app/efood/casa_delicias_arabes//1.jpg', 49.90),
        ('Casa das Delícias Árabes', 'Kebab de Cordeiro', 'O Kebab de Cordeiro é feito com pedaços de cordeiro marinados em especiarias e ervas, grelhados à perfeição e servidos com arroz basmati perfumado, salada e molho de iogurte. Uma opção saborosa e suculenta para quem aprecia a autêntica cozinha árabe.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/casa_delicias_arabes//2.jpg', 54.90),
        ('Casa das Delícias Árabes', 'Shawarma de Frango', 'O Shawarma de Frango é preparado com finas fatias de frango marinadas em uma mistura de especiarias e grelhadas lentamente. Servido com pão pita, salada e molho tahine, este prato é uma opção saborosa e satisfatória para quem deseja saborear a autêntica comida de rua árabe.', '1 pessoa', 'https://api-ebac.vercel.app/efood/casa_delicias_arabes//3.webp', 45.90),
        ('Sakura Sushi House', 'Sushi e Sashimi Combinado', 'O Sushi e Sashimi Combinado é uma seleção de peças cuidadosamente elaboradas por nossos sushimen, incluindo atum, salmão, peixe branco, camarão e outros frutos do mar frescos. Acompanha uma porção de wasabi, gengibre em conserva e molho shoyu, para realçar os sabores naturais dos ingredientes.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/sakura_sushi_house//1.jpg', 89.90),
        ('Sakura Sushi House', 'Tempura de Legumes e Camarão', 'O Tempura de Legumes e Camarão é uma opção deliciosa e crocante, composta por uma variedade de legumes e camarões frescos empanados em uma massa leve e frita até a perfeição. Acompanha um molho tentsuyu, à base de dashi, shoyu e mirin, para dar um toque especial ao prato.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/sakura_sushi_house//2.jpg', 79.90),
        ('Sakura Sushi House', 'Teishoku de Tonkatsu', 'O Teishoku de Tonkatsu é um prato tradicional japonês composto por uma fatia de lombo de porco empanado e frito, servido com arroz japonês, misoshiru (sopa de pasta de soja) e tsukemono (legumes em conserva). O molho tonkatsu, à base de frutas e legumes, adiciona um sabor agridoce irresistível.', '1 pessoa', 'https://api-ebac.vercel.app/efood/sakura_sushi_house//3.jpg', 69.90),
        ('Cantinho Lusitano', 'Bacalhau à Gomes de Sá', 'O Bacalhau à Gomes de Sá é um prato tradicional português, que consiste em lascas de bacalhau cozido, batatas, cebola, alho, azeite e azeitonas pretas. Finalizado com salsa picada e ovos cozidos, este prato é um clássico da culinária portuguesa, que agrada a todos os paladares.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/cantinho_lusitano//1.jpeg', 74.90),
        ('Cantinho Lusitano', 'Arroz de Pato', 'O Arroz de Pato é um delicioso prato português, feito com arroz, carne de pato desfiada, chouriço e cenoura. Cozido lentamente no forno para absorver todos os sabores e aromas, o resultado é um prato saboroso e reconfortante que conquista os corações dos apaixonados pela gastronomia lusitana.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/cantinho_lusitano//2.jpg', 64.90),
        ('Cantinho Lusitano', 'Alheira de Mirandela', 'A Alheira de Mirandela é um emblemático prato português, que consiste em uma deliciosa alheira grelhada, acompanhada de batatas fritas, arroz e uma salada fresca. A alheira é uma saborosa e suculenta mistura de carnes e pão, com um toque de alho e especiarias, que agrada a todos os gostos.', '1 pessoa', 'https://api-ebac.vercel.app/efood/cantinho_lusitano//3.png', 54.90),
        ('Piazza del Forno', 'Pizza Margherita', 'A Pizza Margherita é um clássico italiano, preparada com molho de tomate caseiro, muçarela fresca, folhas de manjericão e um fio de azeite. Simples e deliciosa, esta pizza é a perfeita representação da culinária italiana em sua forma mais pura.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/piazza//1.jpg', 49.90),
        ('Piazza del Forno', 'Pizza Quatro Queijos', 'A Pizza Quatro Queijos é uma combinação irresistível de muçarela, gorgonzola, parmesão e provolone, derretidos harmoniosamente sobre uma massa fina e crocante. Perfeita para os amantes de queijo que desejam uma experiência gastronômica rica e saborosa.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/piazza//2.webp', 59.90),
        ('Piazza del Forno', 'Pizza Calabresa', 'A Pizza Calabresa é uma opção saborosa e suculenta, feita com rodelas de calabresa, cebola roxa fatiada, azeitonas pretas e muçarela derretida. Assada em forno a lenha, esta pizza é a escolha perfeita para quem deseja saborear uma pizza tradicional e deliciosa.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/piazza//3.jpg', 64.90),
        ('Jardim da Terra', 'Hambúrguer de Grão-de-Bico', 'Nosso Hambúrguer de Grão-de-Bico é feito com grão-de-bico, cenoura, cebola e especiarias, servido em um pão vegano fresco com alface, tomate e nosso delicioso molho caseiro. Acompanha batatas rústicas assadas e uma salada fresca e colorida.', '1 pessoa', 'https://api-ebac.vercel.app/efood/jardim_terra//1.webp', 38.90),
        ('Jardim da Terra', 'Lasanha de Berinjela', 'A Lasanha de Berinjela é uma opção saborosa e reconfortante, preparada com camadas de berinjela grelhada, molho de tomate caseiro e um creme de castanha-de-caju. Assada até ficar dourada, esta lasanha vegana é a escolha perfeita para quem busca uma refeição saudável e deliciosa.', '1 a 2 pessoas', 'https://api-ebac.vercel.app/efood/jardim_terra//2.jpeg', 42.90),
        ('Jardim da Terra', 'Bowl de Cogumelos e Quinoa', 'O Bowl de Cogumelos e Quinoa é uma combinação nutritiva e saborosa de quinoa cozida, cogumelos salteados, espinafre, abacate e tomates-cereja. Servido com um molho de ervas frescas e limão, este prato é ideal para quem busca uma refeição leve e saudável.', '1 pessoa', 'https://api-ebac.vercel.app/efood/jardim_terra//3.jpg', 35.90)
)
INSERT INTO shop_product (
    restaurant_id, name, description, portion, image_url,
    price, stock, is_available, is_active
)
SELECT
    r.id, data.name, data.description, data.portion,
    data.image_url, data.price, 30, TRUE, TRUE
FROM original_products data
JOIN shop_user u ON u.username = 'efood_legacy_import' AND u.role = 'merchant'
JOIN shop_restaurant r ON r.owner_id = u.id AND r.name = data.restaurant_name
WHERE NOT EXISTS (
    SELECT 1 FROM shop_product p
    WHERE p.restaurant_id = r.id AND p.name = data.name
);

COMMIT;

-- Safe verification; count should be 6 restaurants and 22 products.
SELECT r.name AS restaurante, COUNT(p.id) AS produtos
FROM shop_restaurant r
JOIN shop_user u ON r.owner_id = u.id
LEFT JOIN shop_product p ON p.restaurant_id = r.id
WHERE u.username = 'efood_legacy_import'
GROUP BY r.id, r.name ORDER BY r.name;

package io.atlas.api.catalog.repository;
import io.atlas.api.catalog.model.CatalogModels.*;
import io.atlas.api.shared.error.ApiFailure;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.http.HttpStatus;
@Repository
public class CatalogRepository {
 private final JdbcTemplate db;
 public CatalogRepository(JdbcTemplate db){this.db=db;}
 private static final String PRODUCT="SELECT p.*,s.server,s.price_cents,(p.active AND s.active) AS effective_active,s.purchasable FROM atlas_web.products p JOIN atlas_web.product_servers s ON s.product_id=p.id ";
 private Product product(ResultSet r,int n)throws SQLException{return new Product(r.getLong("id"),r.getString("slug"),r.getString("name"),r.getString("description"),r.getString("category"),r.getBoolean("effective_active"),r.getString("server"),r.getInt("price_cents"),r.getBoolean("purchasable"),r.getLong("revision"),(Integer)r.getObject("duration_days"),r.getInt("price_cents"),null);}
 public Product product(long id,boolean lock){var rows=db.query(PRODUCT+"WHERE p.id=? AND s.server='emerald'"+(lock?" FOR UPDATE OF p,s":""),this::product,id);if(rows.isEmpty())throw new ApiFailure(HttpStatus.NOT_FOUND,"PRODUCT_NOT_FOUND","Produto não encontrado.");return rows.getFirst();}
 public List<Product> products(boolean admin){return db.query(PRODUCT+"JOIN atlas_web.servers v ON v.slug=s.server WHERE s.server='emerald'"+(admin?"":" AND p.active AND s.active AND v.active")+" ORDER BY p.id",this::product);}
 public List<Promotion> promotions(Instant now,boolean admin){return db.query("SELECT * FROM atlas_web.promotions ORDER BY starts_at,id",(r,n)->{var start=r.getTimestamp("starts_at").toInstant();var end=r.getTimestamp("ends_at").toInstant();var terminal=r.getString("terminal_status");return new Promotion(r.getLong("id"),r.getLong("product_id"),r.getString("server"),r.getString("name"),r.getInt("original_cents"),r.getInt("final_cents"),(Integer)r.getObject("discount_basis_points"),start,end,terminal!=null?terminal:!now.isBefore(end)?"FINISHED":!now.isBefore(start)?"ACTIVE":"SCHEDULED",r.getLong("revision"));}).stream().filter(p->admin||p.status().equals("ACTIVE")||p.status().equals("SCHEDULED")).toList();}
 public long revision(){return db.queryForObject("SELECT revision FROM atlas_web.catalog_state WHERE id=1",Long.class);}
 public void bump(){db.update("UPDATE atlas_web.catalog_state SET revision=revision+1 WHERE id=1");}
 public long create(ProductInput p){long id=db.queryForObject("INSERT INTO atlas_web.products(slug,name,description,category,active,duration_days) VALUES(?,?,?,?,?,CASE WHEN ?='VIPs' THEN 30 ELSE NULL END) RETURNING id",Long.class,p.slug(),p.name().trim(),p.description().trim(),p.category(),p.active(),p.category());db.update("INSERT INTO atlas_web.product_servers(product_id,server,price_cents) VALUES(?,?,?)",id,p.server(),p.priceCents());return id;}
 public void update(long id,ProductInput p){db.update("UPDATE atlas_web.products SET slug=?,name=?,description=?,category=?,active=?,duration_days=CASE WHEN ?='VIPs' THEN 30 ELSE NULL END,revision=revision+1 WHERE id=?",p.slug(),p.name().trim(),p.description().trim(),p.category(),p.active(),p.category(),id);price(id,p.priceCents());}
 public void price(long id,int cents){db.update("UPDATE atlas_web.product_servers SET price_cents=? WHERE product_id=? AND server='emerald'",cents,id);}
 public void increment(long id){db.update("UPDATE atlas_web.products SET revision=revision+1 WHERE id=?",id);}
 public void offer(long id,boolean active){db.update("UPDATE atlas_web.product_servers SET active=? WHERE product_id=? AND server='emerald'",active,id);db.update("UPDATE atlas_web.products SET active=?,revision=revision+1 WHERE id=?",active,id);}
 public long createPromotion(PromotionInput p,int base,int price){return db.queryForObject("INSERT INTO atlas_web.promotions(product_id,server,name,original_cents,final_cents,discount_basis_points,starts_at,ends_at) VALUES(?,?,?,?,?,?,?,?) RETURNING id",Long.class,p.productId(),p.server(),p.name().trim(),base,price,p.discountBasisPoints(),java.sql.Timestamp.from(p.startsAt()),java.sql.Timestamp.from(p.endsAt()));}
 public void updatePromotion(long id,PromotionInput p,int base,int price){db.update("UPDATE atlas_web.promotions SET name=?,original_cents=?,final_cents=?,discount_basis_points=?,starts_at=?,ends_at=?,revision=revision+1 WHERE id=?",p.name().trim(),base,price,p.discountBasisPoints(),java.sql.Timestamp.from(p.startsAt()),java.sql.Timestamp.from(p.endsAt()),id);}
 public void terminal(long id,String status){db.update("UPDATE atlas_web.promotions SET terminal_status=?,revision=revision+1 WHERE id=?",status,id);}
 public boolean invalidPrice(long id,int cents,Instant now){return Boolean.TRUE.equals(db.queryForObject("SELECT EXISTS(SELECT 1 FROM atlas_web.promotions WHERE product_id=? AND terminal_status IS NULL AND ends_at>? AND final_cents>=?)",Boolean.class,id,java.sql.Timestamp.from(now),cents));}
 public void audit(UUID actor,String action,String resource,String before,String after,String requestId){db.update("INSERT INTO atlas_web.catalog_audit(actor,action,resource,before_data,after_data,request_id) VALUES(?,?,?,?::jsonb,?::jsonb,?)",actor,action,resource,before,after,requestId);}
 public void version(long id,long revision,String json){db.update("INSERT INTO atlas_web.product_versions(product_id,revision,snapshot) VALUES(?,?,?::jsonb)",id,revision,json);}
}

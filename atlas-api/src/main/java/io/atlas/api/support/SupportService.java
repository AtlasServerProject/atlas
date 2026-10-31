package io.atlas.api.support;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import io.atlas.api.shared.error.ApiFailure;
import io.atlas.api.auth.service.AuthService;
import io.atlas.api.commerce.service.OrderService;
import io.atlas.api.commerce.model.CommerceModels.OrderView;
import io.atlas.api.payment.PaymentRepository;
@Service
public class SupportService {
 public record Page(List<SupportRepository.Ticket> items,int page,boolean hasNext){}
 public record TeamPage(List<SupportRepository.Member> items,int page,boolean hasNext){}
 @Transactional(readOnly=true) public TeamPage team(UUID user,int page){if(!"ADMIN".equals(auth.current(user).role().toString()))throw new ApiFailure(HttpStatus.FORBIDDEN,"ACCESS_DENIED","Acesso não autorizado.");pageNumber(page);var items=repo.team(page);return new TeamPage(items.stream().limit(20).toList(),page,items.size()>20);}
 public record Detail(SupportRepository.Ticket ticket,OrderView order,List<PaymentRepository.ReceiptPayment> payments,List<SupportRepository.Message> messages,boolean hasMore){}
 private final SupportRepository repo;private final OrderService orders;private final AuthService auth;private final PaymentRepository payments;
 public SupportService(SupportRepository repo,OrderService orders,AuthService auth,PaymentRepository payments){this.repo=repo;this.orders=orders;this.auth=auth;this.payments=payments;}
 private boolean staff(UUID user){return Set.of("ADMIN","SUPPORT","MODERATOR").contains(auth.current(user).role().toString());}
 private void requireStaff(UUID user){if(!staff(user))throw new ApiFailure(HttpStatus.FORBIDDEN,"ACCESS_DENIED","Acesso não autorizado.");}
 private SupportRepository.Ticket allowed(UUID user,UUID id,boolean admin,boolean lock){if(admin)requireStaff(user);var t=repo.find(id,lock);if(t==null||(!admin&&!t.userId().equals(user)))throw new ApiFailure(HttpStatus.NOT_FOUND,"TICKET_NOT_FOUND","Ticket não encontrado.");return t;}
 private void pageNumber(int page){if(page<0||page>100000)throw new ApiFailure(HttpStatus.BAD_REQUEST,"INVALID_PAGE","Página inválida.");}
 @Transactional public SupportRepository.Ticket create(UUID user,UUID order,String title,String body){orders.detail(user,order);repo.lockOrder(order);var old=repo.forOrder(order);if(old!=null)return old;UUID id=UUID.randomUUID();repo.create(id,order,user,title.trim());repo.message(id,user,"CUSTOMER",body.trim());return repo.find(id,false);}
 @Transactional(readOnly=true) public Page list(UUID user,boolean admin,int page){pageNumber(page);if(admin)requireStaff(user);var items=repo.list(admin?null:user,page);return new Page(items.stream().limit(20).toList(),page,items.size()>20);}
 @Transactional(readOnly=true) public Detail detail(UUID user,UUID id,boolean admin,int after){if(after<0)throw new ApiFailure(HttpStatus.BAD_REQUEST,"INVALID_CURSOR","Cursor inválido.");var t=allowed(user,id,admin,false);var messages=repo.messages(id,after);return new Detail(t,orders.detail(t.userId(),t.orderId()),payments.receiptPayments(t.orderId()),messages.stream().limit(100).toList(),messages.size()>100);}
 @Transactional public void reply(UUID user,UUID id,boolean admin,String body){var t=allowed(user,id,admin,true);repo.message(id,user,admin?"STAFF":"CUSTOMER",body.trim());repo.status(id,admin?"WAITING_CUSTOMER":"OPEN");}
 @Transactional public void status(UUID user,UUID id,String status){requireStaff(user);var t=allowed(user,id,true,true);if(!Set.of("OPEN","IN_PROGRESS","WAITING_CUSTOMER","RESOLVED").contains(status))throw new ApiFailure(HttpStatus.BAD_REQUEST,"INVALID_STATUS","Status inválido.");if(!status.equals(t.status())){repo.message(id,user,"STATUS",status);repo.status(id,status);}}
}

package lab.rollback;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.stereotype.Component;

/**
 * Spring Data 저장소가 아닌 평범한 빈에서 EntityManager 를 직접 쓴다.
 * @Repository 가 아니므로 예외 변환 후처리기(PersistenceExceptionTranslationPostProcessor)가 붙지 않는다.
 */
@Component
public class EmWork {
    @PersistenceContext
    EntityManager em;

    void note(String who) { em.persist(new Note(who)); em.flush(); }

    void touch(int id) { em.find(Item.class, id).v++; em.flush(); }
}

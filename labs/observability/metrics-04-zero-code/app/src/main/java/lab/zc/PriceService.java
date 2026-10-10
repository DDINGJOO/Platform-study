package lab.zc;

import java.math.BigDecimal;
import java.math.MathContext;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import org.springframework.stereotype.Service;

@Service
public class PriceService {

    /** 상품 items 개에 할인 규칙을 적용한 합계. 일부러 무겁게 만든 계산이다. */
    public BigDecimal quote(String sku, int items) {
        BigDecimal total = BigDecimal.ZERO;
        for (int i = 0; i < items; i++) {
            total = total.add(applyDiscountRules(sku, i));
        }
        return total;
    }

    BigDecimal applyDiscountRules(String sku, int i) {
        BigDecimal base = BigDecimal.valueOf(1000 + (couponHash(sku, i) % 500));
        // 복리 할인을 고정밀도로 계산한다: 이 줄이 CPU 를 가장 많이 쓰게 된다
        return base.multiply(BigDecimal.valueOf(0.997).pow(64, MathContext.DECIMAL128));
    }

    int couponHash(String sku, int i) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] d = md.digest((sku + ":" + i).getBytes());
            return ((d[0] & 0xff) << 8) | (d[1] & 0xff);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}

package com.singular.segment_integration;

import android.app.Activity;
import android.os.Bundle;

import com.segment.analytics.Analytics;
import com.segment.analytics.ValueMap;
import com.segment.analytics.integrations.IdentifyPayload;
import com.segment.analytics.integrations.Integration;
import com.segment.analytics.integrations.TrackPayload;
import com.singular.sdk.Singular;
import com.singular.sdk.internal.Utils;

public class SingularIntegration extends Integration<Singular> {

    private static final String SINGULAR_KEY = "Singular";

    public static final Factory FACTORY = new Factory() {
        @Override
        public Integration<?> create(ValueMap settings, Analytics analytics) {
            return new SingularIntegration(settings, analytics);
        }

        @Override
        public String key() {
            return SINGULAR_KEY;
        }
    };

    public SingularIntegration(ValueMap settings, Analytics analytics) {
        super();
        String apiKey = settings.getString("apikey");
        String secret = settings.getString("secret");
        Singular.init(analytics.getApplication().getApplicationContext(), apiKey, secret);
    }

    @Override
    public void identify(IdentifyPayload identify) {
        super.identify(identify);
        Singular.setCustomUserId(identify.userId());
    }

    @Override
    public void track(TrackPayload track) {
        super.track(track);

        if (track.properties().revenue() == 0) {
            Singular.event(track.event());
        } else {
            String currency = track.properties().currency();

            if (Utils.isEmptyOrNull(currency)) {
                currency = "USD";
            }

            Singular.customRevenue(track.event(), currency, track.properties().revenue());
        }
    }
}
